"""
naver_checker (네이버 공식 오픈API) 단위 테스트
- 실제 API 호출 없이 mock 응답으로 5가지 케이스 검증:
  ①정상 노출(나무위키·유튜브) ②일부 미노출 ③키 없음 ④HTTP 429/401 ⑤<b> 태그 제거
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import naver_checker


class _FakeResp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.content = b"x" * 1000

    def json(self):
        return self._payload


def _keys(monkeypatch):
    monkeypatch.setenv("NAVER_CLIENT_ID", "cid")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "csecret")


# ── ① 정상 노출 (나무위키·유튜브) ────────────────────────────
def test_presence_found(monkeypatch):
    _keys(monkeypatch)
    payload = {"items": [
        {"title": "이후(소설가)", "link": "https://namu.wiki/w/이후(소설가)",
         "description": "대한민국의 <b>소설가</b>"},
        {"title": "이후 채널", "link": "https://www.youtube.com/channel/UC3iQTM8DVgzRhgArrSIPp2g",
         "description": "유튜브 채널"},
    ]}
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        return _FakeResp(200, payload)

    monkeypatch.setattr(naver_checker.requests, "get", fake_get)
    r = naver_checker.check_naver_presence("소설가 이후")
    assert r["status"] == "ok"
    assert captured["url"] == "https://openapi.naver.com/v1/search/webkr.json"
    assert captured["headers"]["X-Naver-Client-Id"] == "cid"
    assert captured["headers"]["X-Naver-Client-Secret"] == "csecret"
    haystack = " ".join(r["links"])
    assert "namu.wiki" in haystack
    assert "youtube.com" in haystack
    assert len(r["items"]) == 2


# ── ② 일부 미노출 ────────────────────────────────────────────
def test_presence_partial(monkeypatch):
    _keys(monkeypatch)
    payload = {"items": [
        {"title": "무관", "link": "https://example.com/x", "description": "다른 내용"},
    ]}
    monkeypatch.setattr(naver_checker.requests, "get",
                        lambda *a, **k: _FakeResp(200, payload))
    r = naver_checker.check_naver_presence("소설가 이후")
    assert r["status"] == "ok"
    haystack = " ".join(r["links"])
    assert "namu.wiki" not in haystack
    assert "kyobobook.co.kr" not in haystack


# ── ③ 키 없음 ────────────────────────────────────────────────
def test_no_api_key(monkeypatch):
    monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)

    def fail(*a, **k):
        raise AssertionError("키가 없으면 네트워크 요청을 하면 안 됨")
    monkeypatch.setattr(naver_checker.requests, "get", fail)
    r = naver_checker.check_naver_presence("소설가 이후")
    assert r == {"status": "no_api_key"}


# ── ④ HTTP 401 / 429 ─────────────────────────────────────────
def test_http_401(monkeypatch):
    _keys(monkeypatch)
    payload = {"errorMessage": "Not Exist Client ID", "errorCode": "024"}
    monkeypatch.setattr(naver_checker.requests, "get",
                        lambda *a, **k: _FakeResp(401, payload))
    r = naver_checker.check_naver_presence("소설가 이후")
    assert r["status"] == "error"
    assert "401" in r["detail"] and "Client ID" in r["detail"]


def test_http_429(monkeypatch):
    _keys(monkeypatch)
    monkeypatch.setattr(naver_checker.requests, "get",
                        lambda *a, **k: _FakeResp(429, {"errorMessage": "Rate exceeded"}))
    r = naver_checker.check_naver_presence("소설가 이후")
    assert r["status"] == "error"
    assert "429" in r["detail"]


# ── ⑤ <b> 태그 제거 ──────────────────────────────────────────
def test_strip_tags():
    assert naver_checker.strip_tags("대한민국의 <b>소설가</b> 이후") == "대한민국의 소설가 이후"
    assert naver_checker.strip_tags("") == ""


def test_tags_stripped_in_items(monkeypatch):
    _keys(monkeypatch)
    payload = {"items": [
        {"title": "<b>이후</b> (소설가)", "link": "https://namu.wiki/w/x",
         "description": "<b>소설가</b> 이후의 작품"},
    ]}
    monkeypatch.setattr(naver_checker.requests, "get",
                        lambda *a, **k: _FakeResp(200, payload))
    r = naver_checker.check_naver_presence("소설가 이후")
    it = r["items"][0]
    assert "<b>" not in it["title"] and "</b>" not in it["title"]
    assert "<b>" not in it["description"]
    assert it["title"] == "이후 (소설가)"
