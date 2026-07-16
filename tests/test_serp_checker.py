"""
serp_checker (Google Custom Search API) 단위 테스트
- 실제 API 호출 없이 mock 응답으로 4가지 케이스 검증:
  ① 정상 노출 ② 미노출 ③ API 키 없음 ④ HTTP 429(쿼터 초과)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import serp_checker


NEEDLES = {
    "위키백과 문서": ["ko.wikipedia.org"],
    "교보문고 작가 페이지": ["kyobobook.co.kr"],
}


class _FakeResp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.content = b"x" * 1000

    def json(self):
        return self._payload


def _set_keys(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CSE_CX", "test-cx")


# ── ① 정상 노출 ──────────────────────────────────────────────
def test_presence_found(monkeypatch):
    _set_keys(monkeypatch)
    payload = {"items": [
        {"link": "https://ko.wikipedia.org/wiki/이후", "displayLink": "ko.wikipedia.org",
         "title": "이후 (소설가)", "snippet": "대한민국의 소설가"},
        {"link": "https://store.kyobobook.co.kr/person/detail/1", "displayLink": "store.kyobobook.co.kr",
         "title": "이후 | 소설가", "snippet": "작가 이후"},
    ]}
    calls = []
    monkeypatch.setattr(serp_checker.requests, "get",
                        lambda *a, **k: calls.append(k) or _FakeResp(200, payload))
    r = serp_checker.check_google_presence("소설가 이후", NEEDLES)
    assert r["status"] == "ok"
    assert r["found"] == {"위키백과 문서": True, "교보문고 작가 페이지": True}
    assert "소설가" in r["relevance_text"]
    # 전부 찾았으므로 2페이지 조회 안 함 (쿼터 절약)
    assert len(calls) == 1


# ── ② 미노출 ─────────────────────────────────────────────────
def test_presence_not_found(monkeypatch):
    _set_keys(monkeypatch)
    payload = {"items": [
        {"link": "https://example.com/other", "displayLink": "example.com",
         "title": "무관한 결과", "snippet": "다른 내용"},
    ]}
    calls = []
    monkeypatch.setattr(serp_checker.requests, "get",
                        lambda *a, **k: calls.append(k) or _FakeResp(200, payload))
    r = serp_checker.check_google_presence("소설가 이후", NEEDLES)
    assert r["status"] == "ok"
    assert r["found"] == {"위키백과 문서": False, "교보문고 작가 페이지": False}
    # 미노출 needle이 남아 있으므로 2페이지(start=11)까지 조회
    assert len(calls) == 2
    assert calls[1]["params"]["start"] == 11


# ── ③ API 키 없음 ────────────────────────────────────────────
def test_no_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_CX", raising=False)

    def fail(*a, **k):
        raise AssertionError("키가 없으면 네트워크 요청을 하면 안 됨")
    monkeypatch.setattr(serp_checker.requests, "get", fail)
    r = serp_checker.check_google_presence("소설가 이후", NEEDLES)
    assert r == {"status": "no_api_key"}


# ── ④ HTTP 429 (쿼터 초과) ───────────────────────────────────
def test_quota_exceeded(monkeypatch):
    _set_keys(monkeypatch)
    payload = {"error": {"code": 429, "message": "Quota exceeded for quota metric 'Queries'"}}
    monkeypatch.setattr(serp_checker.requests, "get",
                        lambda *a, **k: _FakeResp(429, payload))
    r = serp_checker.check_google_presence("소설가 이후", NEEDLES)
    assert r["status"] == "error"
    assert "429" in r["detail"] and "Quota" in r["detail"]
