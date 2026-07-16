"""
serp_checker (Serper.dev API) 단위 테스트
- 실제 API 호출 없이 mock 응답으로 4가지 케이스 검증:
  ① 정상 노출 ② 미노출 ③ API 키 없음 ④ HTTP 403/429(키 문제/쿼터 초과)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import serp_checker


class _FakeResp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.content = b"x" * 1000

    def json(self):
        return self._payload


# ── ① 정상 노출 ──────────────────────────────────────────────
def test_presence_found(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    payload = {"organic": [
        {"link": "https://ko.wikipedia.org/wiki/이후", "title": "이후 (소설가)",
         "snippet": "대한민국의 소설가"},
        {"link": "https://store.kyobobook.co.kr/person/detail/1", "title": "이후 | 소설가",
         "snippet": "작가 이후"},
    ]}
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResp(200, payload)

    monkeypatch.setattr(serp_checker.requests, "post", fake_post)
    r = serp_checker.check_google_presence("소설가 이후")
    assert r["status"] == "ok"
    # 올바른 엔드포인트·인증 헤더·본문
    assert captured["url"] == "https://google.serper.dev/search"
    assert captured["headers"]["X-API-KEY"] == "test-key"
    assert captured["json"]["q"] == "소설가 이후"
    # 링크 안에 두 대상 도메인이 모두 들어 있어야 함
    haystack = " ".join(r["links"])
    assert "ko.wikipedia.org" in haystack
    assert "kyobobook.co.kr" in haystack
    assert "소설가" in r["relevance_text"]
    assert r["total_results"] == 2


# ── ② 미노출 ─────────────────────────────────────────────────
def test_presence_not_found(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    payload = {"organic": [
        {"link": "https://example.com/other", "title": "무관한 결과", "snippet": "다른 내용"},
    ]}
    monkeypatch.setattr(serp_checker.requests, "post",
                        lambda *a, **k: _FakeResp(200, payload))
    r = serp_checker.check_google_presence("소설가 이후")
    assert r["status"] == "ok"
    haystack = " ".join(r["links"])
    assert "ko.wikipedia.org" not in haystack
    assert "kyobobook.co.kr" not in haystack


# ── ③ API 키 없음 ────────────────────────────────────────────
def test_no_api_key(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)

    def fail(*a, **k):
        raise AssertionError("키가 없으면 네트워크 요청을 하면 안 됨")
    monkeypatch.setattr(serp_checker.requests, "post", fail)
    r = serp_checker.check_google_presence("소설가 이후")
    assert r == {"status": "no_api_key"}


# ── ④ HTTP 403 (키 문제) / 429 (쿼터 초과) ───────────────────
def test_http_error(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    payload = {"message": "Unauthorized"}
    monkeypatch.setattr(serp_checker.requests, "post",
                        lambda *a, **k: _FakeResp(403, payload))
    r = serp_checker.check_google_presence("소설가 이후")
    assert r["status"] == "error"
    assert "403" in r["detail"] and "Unauthorized" in r["detail"]


def test_quota_exceeded(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    monkeypatch.setattr(serp_checker.requests, "post",
                        lambda *a, **k: _FakeResp(429, {"message": "Not enough credits"}))
    r = serp_checker.check_google_presence("소설가 이후")
    assert r["status"] == "error"
    assert "429" in r["detail"]
