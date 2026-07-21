import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversation_parser import (
    Conversation,
    ConversationError,
    Message,
    conversation_to_markdown,
    fetch_share_page,
    parse_conversation,
    sanitize_filename,
    validate_share_url,
)


def test_supported_share_urls_and_ssrf_boundary():
    assert validate_share_url("https://chatgpt.com/share/12345678-abcd")[0] == "chatgpt"
    assert validate_share_url("https://claude.ai/share/abcdefgh-1234")[0] == "claude"
    with pytest.raises(ConversationError, match="공유 링크만"):
        validate_share_url("https://chatgpt.com.evil.example/share/12345678")
    with pytest.raises(ConversationError, match="HTTPS"):
        validate_share_url("http://chatgpt.com/share/12345678")
    with pytest.raises(ConversationError, match="형식"):
        validate_share_url("https://chatgpt.com/backend-api/conversation/12345678")


CHAT_HTML = """<!doctype html><html><head>
<meta property="og:title" content="파서 테스트 - ChatGPT"></head><body><main>
<article data-message-author-role="user"><p>표와 <a href="https://example.com">링크</a>를 보여줘.</p></article>
<article data-message-author-role="assistant">
  <p>결과입니다.</p><pre><code class="language-python">print("ok")</code></pre>
  <table><tr><th>이름</th><th>값</th></tr><tr><td>A</td><td>1</td></tr></table>
  <ul><li>첫째</li><li>둘째</li></ul>
</article></main></body></html>"""


def test_dom_parser_preserves_roles_code_tables_lists_and_links():
    conversation = parse_conversation("chatgpt", "https://chatgpt.com/share/12345678", CHAT_HTML)
    assert conversation.title == "파서 테스트"
    assert [message.role for message in conversation.messages] == ["user", "assistant"]
    user, assistant = conversation.messages
    assert "[링크](https://example.com)" in user.content
    assert "```python" in assistant.content
    assert "| 이름 | 값 |" in assistant.content
    assert "- 첫째" in assistant.content


def test_next_json_parser_extracts_messages_when_dom_is_not_rendered():
    data = {
        "props": {
            "pageProps": {
                "mapping": [
                    {"message": {"author": {"role": "user"}, "content": {"parts": ["질문"]}}},
                    {"message": {"author": {"role": "assistant"}, "content": {"parts": ["답변"]}}},
                ]
            }
        }
    }
    import json

    html = f'<html><head><title>JSON 대화 | Claude</title></head><body><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></body></html>'
    conversation = parse_conversation("claude", "https://claude.ai/share/abcdefgh", html)
    assert [(m.role, m.content) for m in conversation.messages] == [("user", "질문"), ("assistant", "답변")]


def test_markdown_frontmatter_filename_and_windows_safety():
    conversation = Conversation(
        provider="claude",
        title='CON: 계획/검토? "완료"',
        source_url="https://claude.ai/share/abcdefgh",
        messages=[Message("user", "질문"), Message("assistant", "답변")],
    )
    markdown, filename = conversation_to_markdown(
        conversation, datetime(2026, 7, 21, 12, 34, 56, tzinfo=timezone.utc)
    )
    assert markdown.startswith("---\ntitle:")
    assert 'source: "https://claude.ai/share/abcdefgh"' in markdown
    assert "provider: Claude" in markdown
    assert "downloaded_at: 2026-07-21T12:34:56+00:00" in markdown
    assert "## 사용자" in markdown and "## Claude" in markdown
    assert not any(ch in filename for ch in '<>:"/\\|?*')
    assert filename.endswith("_20260721_123456.md")
    assert sanitize_filename("CON") == "_CON"


class FakeResponse:
    def __init__(self, status, headers=None, body=b""):
        self.status_code = status
        self.headers = headers or {}
        self.body = body
        self.encoding = "utf-8"
        self.closed = False

    def iter_content(self, _size):
        yield self.body

    def close(self):
        self.closed = True


class FakeHttp:
    def __init__(self, responses):
        self.responses = iter(responses)

    def get(self, *_args, **_kwargs):
        return next(self.responses)


def test_fetch_rejects_redirect_outside_supported_hosts():
    http = FakeHttp([FakeResponse(302, {"Location": "https://evil.example/share/abcdefgh"})])
    with pytest.raises(ConversationError, match="공유 링크만"):
        fetch_share_page("https://claude.ai/share/abcdefgh", http=http)


def test_fetch_maps_private_and_expired_links_to_clear_errors():
    with pytest.raises(ConversationError, match="권한") as private:
        fetch_share_page(
            "https://chatgpt.com/share/12345678", http=FakeHttp([FakeResponse(403)])
        )
    assert private.value.status == 403
    with pytest.raises(ConversationError, match="만료") as expired:
        fetch_share_page(
            "https://claude.ai/share/abcdefgh", http=FakeHttp([FakeResponse(410)])
        )
    assert expired.value.status == 404


def test_browser_storage_uses_permissioned_directory_and_safe_duplicate_names():
    source = (os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    js = open(os.path.join(source, "static", "obsidian.js"), encoding="utf-8").read()
    assert "showDirectoryPicker" in js
    assert "indexedDB" in js
    assert "queryPermission" in js and "requestPermission" in js
    assert "uniqueFileHandle" in js and "NotFoundError" in js
    assert "browserDownload" in js

