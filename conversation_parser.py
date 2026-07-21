"""Fetch public ChatGPT/Claude shares and convert their visible messages to Markdown."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))
}
SUPPORTED = {
    "chatgpt": {"chatgpt.com", "www.chatgpt.com", "chat.openai.com"},
    "claude": {"claude.ai", "www.claude.ai"},
}


class ConversationError(RuntimeError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Conversation:
    provider: str
    title: str
    source_url: str
    messages: list[Message]


def validate_share_url(value: str) -> tuple[str, str]:
    value = str(value or "").strip()
    if not value or len(value) > 2048:
        raise ConversationError("공유 링크를 입력해 주세요.", 400)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise ConversationError("HTTPS 공유 링크만 지원합니다.", 400)
    host = (parsed.hostname or "").lower().rstrip(".")
    provider = next((name for name, hosts in SUPPORTED.items() if host in hosts), "")
    if not provider:
        raise ConversationError("chatgpt.com 또는 claude.ai의 공유 링크만 지원합니다.", 400)
    path = parsed.path.rstrip("/")
    if provider == "chatgpt" and not re.fullmatch(r"/share/[A-Za-z0-9-]{8,100}", path):
        raise ConversationError("ChatGPT 공유 링크 형식이 올바르지 않습니다.", 400)
    if provider == "claude" and not re.fullmatch(r"/share/[A-Za-z0-9-]{8,100}", path):
        raise ConversationError("Claude 공유 링크 형식이 올바르지 않습니다.", 400)
    clean = parsed._replace(fragment="").geturl()
    return provider, clean


def fetch_share_page(url: str, http=None) -> tuple[str, str, str]:
    provider, current = validate_share_url(url)
    http = http or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SeoblueObsidian/1.0; +https://seo.xn--hu5b23z.com)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
    }
    for _ in range(MAX_REDIRECTS + 1):
        try:
            response = http.get(current, headers=headers, timeout=20, allow_redirects=False, stream=True)
        except requests.RequestException as exc:
            raise ConversationError("공유 페이지에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", 502) from exc
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location", "")
            response.close()
            if not location:
                raise ConversationError("공유 페이지의 이동 주소가 올바르지 않습니다.", 502)
            next_url = urljoin(current, location)
            next_provider, current = validate_share_url(next_url)
            if next_provider != provider:
                raise ConversationError("지원하지 않는 주소로 이동되어 가져오기를 중단했습니다.", 400)
            continue
        if response.status_code in {401, 403}:
            response.close()
            raise ConversationError("로그인 또는 접근 권한이 필요한 대화입니다.", 403)
        if response.status_code in {404, 410}:
            response.close()
            raise ConversationError("공유 링크가 없거나 만료·해제되었습니다.", 404)
        if response.status_code != 200:
            status = response.status_code
            response.close()
            raise ConversationError(f"공유 페이지를 가져오지 못했습니다. (HTTP {status})", 502)
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            response.close()
            raise ConversationError("공유 링크가 HTML 페이지를 반환하지 않았습니다.", 422)
        content = bytearray()
        for chunk in response.iter_content(64 * 1024):
            content.extend(chunk)
            if len(content) > MAX_PAGE_BYTES:
                response.close()
                raise ConversationError("공유 페이지가 너무 커서 안전하게 처리할 수 없습니다.", 413)
        encoding = response.encoding or "utf-8"
        response.close()
        return provider, current, bytes(content).decode(encoding, errors="replace")
    raise ConversationError("공유 페이지가 너무 많이 이동되어 가져오기를 중단했습니다.", 400)


def _clean_text(value) -> str:
    return re.sub(r"\n{3,}", "\n\n", str(value or "").replace("\r\n", "\n").strip())


def _content_text(value) -> str:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, list):
        return _clean_text("\n\n".join(filter(None, (_content_text(item) for item in value))))
    if not isinstance(value, dict):
        return ""
    if isinstance(value.get("parts"), list):
        return _content_text(value["parts"])
    for key in ("text", "value", "content"):
        if key in value:
            text = _content_text(value[key])
            if text:
                return text
    return ""


def _role(value) -> str:
    value = str(value or "").lower()
    if value in {"user", "human"} or "user" in value or "human" in value:
        return "user"
    if value in {"assistant", "ai", "claude"} or "assistant" in value or "claude" in value:
        return "assistant"
    return ""


def _walk_json(value, found: list[Message], seen: set[tuple[str, str]]) -> None:
    if isinstance(value, dict):
        author = value.get("author")
        role = _role(author.get("role") if isinstance(author, dict) else value.get("role") or value.get("sender"))
        content = _content_text(value.get("content") if "content" in value else value.get("text"))
        if role and content:
            key = (role, content)
            if key not in seen:
                found.append(Message(role, content))
                seen.add(key)
        for child in value.values():
            _walk_json(child, found, seen)
    elif isinstance(value, list):
        for child in value:
            _walk_json(child, found, seen)


def _node_markdown(node, depth=0) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""
    name = node.name.lower()
    if name in {"script", "style", "button", "svg", "noscript"}:
        return ""
    if name == "br":
        return "\n"
    if name == "pre":
        code = node.get_text("", strip=False).strip("\n")
        code_node = node.find("code")
        language = ""
        if code_node:
            classes = " ".join(code_node.get("class", []))
            match = re.search(r"(?:language-|lang-)([\w+-]+)", classes)
            language = match.group(1) if match else ""
        fence = "````" if "```" in code else "```"
        return f"\n{fence}{language}\n{code}\n{fence}\n"
    if name == "code":
        value = node.get_text("", strip=False)
        marker = "``" if "`" in value else "`"
        return f"{marker}{value}{marker}"
    if name == "a":
        label = _clean_text("".join(_node_markdown(c, depth) for c in node.children))
        href = node.get("href", "")
        return f"[{label}]({href})" if label and href else label
    if name in {"strong", "b"}:
        return f"**{''.join(_node_markdown(c, depth) for c in node.children).strip()}**"
    if name in {"em", "i"}:
        return f"*{''.join(_node_markdown(c, depth) for c in node.children).strip()}*"
    if name == "blockquote":
        body = _clean_text("".join(_node_markdown(c, depth) for c in node.children))
        return "\n" + "\n".join(f"> {line}" for line in body.splitlines()) + "\n"
    if name in {"ul", "ol"}:
        lines = []
        for index, li in enumerate(node.find_all("li", recursive=False), 1):
            prefix = f"{index}." if name == "ol" else "-"
            lines.append(f"{prefix} {_clean_text(''.join(_node_markdown(c, depth + 1) for c in li.children))}")
        return "\n" + "\n".join(lines) + "\n"
    if name == "table":
        rows = []
        for tr in node.find_all("tr"):
            cells = [_clean_text(cell.get_text(" ", strip=True)).replace("|", "\\|") for cell in tr.find_all(["th", "td"], recursive=False)]
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        width = max(map(len, rows))
        rows = [row + [""] * (width - len(row)) for row in rows]
        lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
        lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
        return "\n" + "\n".join(lines) + "\n"
    body = "".join(_node_markdown(child, depth) for child in node.children)
    if re.fullmatch(r"h[1-6]", name):
        return f"\n{'#' * int(name[1])} {_clean_text(body)}\n"
    if name in {"p", "div", "section", "article", "li"}:
        return f"\n{body.strip()}\n"
    return body


def html_to_markdown(node: Tag) -> str:
    return _clean_text(unescape(_node_markdown(node)))


def _messages_from_dom(soup: BeautifulSoup) -> list[Message]:
    messages, used = [], set()
    selectors = [
        "[data-message-author-role]",
        "[data-testid*='user-message']",
        "[data-testid*='assistant-message']",
        "[data-author-role]",
    ]
    for node in soup.select(",".join(selectors)):
        marker = " ".join(
            str(node.get(key, "")) for key in ("data-message-author-role", "data-author-role", "data-testid")
        )
        role = _role(marker)
        content = html_to_markdown(node)
        key = (role, content)
        if role and content and key not in used:
            messages.append(Message(role, content))
            used.add(key)
    return messages


def _messages_from_scripts(soup: BeautifulSoup) -> list[Message]:
    messages: list[Message] = []
    seen: set[tuple[str, str]] = set()
    for script in soup.find_all("script"):
        raw = script.string or script.get_text("", strip=False)
        if not raw or len(raw) > MAX_PAGE_BYTES:
            continue
        candidates = []
        if script.get("type") in {"application/json", "application/ld+json"} or script.get("id") == "__NEXT_DATA__":
            candidates.append(raw)
        candidates.extend(match.group(1) for match in re.finditer(r"(?s)(\{\s*\"(?:mapping|messages|conversation|chat_messages)\".*\})", raw))
        for candidate in candidates:
            try:
                _walk_json(json.loads(candidate), messages, seen)
            except (json.JSONDecodeError, RecursionError):
                continue
    return messages


def parse_conversation(provider: str, source_url: str, html: str) -> Conversation:
    soup = BeautifulSoup(html, "lxml")
    title_node = soup.select_one("meta[property='og:title']")
    title = title_node.get("content", "") if title_node else ""
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)
    title = re.sub(r"\s*[|·-]\s*(ChatGPT|Claude)\s*$", "", title, flags=re.I).strip()
    title = title or ("ChatGPT 대화" if provider == "chatgpt" else "Claude 대화")
    messages = _messages_from_dom(soup)
    if not messages:
        messages = _messages_from_scripts(soup)
    if not messages:
        page_text = soup.get_text(" ", strip=True).lower()
        if any(term in page_text for term in ("log in", "sign in", "로그인", "access denied")):
            raise ConversationError("로그인 또는 접근 권한이 필요한 대화입니다.", 403)
        raise ConversationError("공유 페이지에서 대화 메시지를 찾지 못했습니다. 링크가 공개 상태인지 확인해 주세요.")
    return Conversation(provider=provider, title=title, source_url=source_url, messages=messages)


def sanitize_filename(title: str) -> str:
    value = unicodedata.normalize("NFKC", str(title or "대화"))
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")[:100] or "대화"
    if value.split(".")[0].upper() in WINDOWS_RESERVED:
        value = f"_{value}"
    return value


def conversation_to_markdown(conversation: Conversation, downloaded_at=None) -> tuple[str, str]:
    downloaded_at = downloaded_at or datetime.now(timezone.utc)
    provider_label = "ChatGPT" if conversation.provider == "chatgpt" else "Claude"
    yaml_title = json.dumps(conversation.title, ensure_ascii=False)
    yaml_url = json.dumps(conversation.source_url, ensure_ascii=False)
    parts = [
        "---",
        f"title: {yaml_title}",
        f"source: {yaml_url}",
        f"provider: {provider_label}",
        f"downloaded_at: {downloaded_at.isoformat(timespec='seconds')}",
        "---",
        "",
        f"# {conversation.title}",
    ]
    for message in conversation.messages:
        label = "사용자" if message.role == "user" else provider_label
        parts.extend(["", f"## {label}", "", message.content.strip()])
    markdown = "\n".join(parts).rstrip() + "\n"
    date = downloaded_at.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return markdown, f"{sanitize_filename(conversation.title)}_{date}.md"


def convert_share_url(url: str, http=None) -> tuple[Conversation, str, str]:
    provider, final_url, html = fetch_share_page(url, http=http)
    conversation = parse_conversation(provider, final_url, html)
    markdown, filename = conversation_to_markdown(conversation)
    return conversation, markdown, filename

