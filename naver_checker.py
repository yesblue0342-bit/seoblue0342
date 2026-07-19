"""
네이버 노출 체커 — 네이버 공식 오픈API (openapi.naver.com)
- 네이버 통합검색 HTML 스크래핑은 봇 차단/구조 변경으로 파싱이 실패하므로,
  공식 오픈API(webkr: 웹문서 검색)로 실제 결과를 받아 노출 여부를 판정한다.
- 인증은 환경변수로만 주입 (코드/저장소에 키를 두지 않는다):
    NAVER_CLIENT_ID     : 네이버 개발자센터에서 발급한 애플리케이션 Client ID
    NAVER_CLIENT_SECRET : 같은 애플리케이션의 Client Secret
- 무료(일 25,000회), 봇 차단 없음.

주의 — '순위'가 아니라 '노출 여부'다:
  오픈API webkr 결과의 순서는 사용자가 보는 통합검색 화면의 순위와 일치하지 않는다.
  따라서 "몇 위"를 표시하면 거짓 정보가 되므로, 각 타깃의 노출 O/X + 발견 URL만 다룬다.
"""

import os
import re
import time

import requests

NAVER_ENDPOINT = "https://openapi.naver.com/v1/search/webkr.json"

# <b>...</b> 등 하이라이트/HTML 태그 제거용
_TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(text: str) -> str:
    """네이버 응답의 <b> 하이라이트 등 HTML 태그 제거."""
    return _TAG_RE.sub("", text or "")


def check_naver_presence(query: str, num: int = 10, max_pages: int = 2) -> dict:
    """네이버 오픈API(webkr)로 검색결과를 받아 링크·항목을 반환한다.

    노출 여부 판정(도메인 매칭)은 호출측(rank_monitor)에서 수행한다.
    Returns (status 별 형태):
      {"status": "no_api_key"}
      {"status": "error", "detail": "..."}
      {"status": "ok", "links": [str, ...],
       "items": [{"title": str, "link": str, "description": str}, ...],
       "api_meta": {"response_time": ms, "content_length": bytes}}
    """
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {"status": "no_api_key"}

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    items = []
    links = []
    response_time = 0
    content_length = 0

    for page in range(max_pages):
        params = {"query": query, "display": num, "start": page * num + 1}
        try:
            t0 = time.time()
            resp = requests.get(NAVER_ENDPOINT, headers=headers, params=params, timeout=15)
            response_time += round((time.time() - t0) * 1000)
            content_length += len(resp.content)
            if resp.status_code != 200:
                # 401(키 오류)·429(쿼터 초과)·5xx 등 — 부분 결과로 오판하지 않도록 전체 오류 처리
                try:
                    body = resp.json()
                    detail = body.get("errorMessage") or body.get("message") or resp.text[:200]
                except ValueError:
                    detail = resp.text[:200]
                return {"status": "error", "detail": f"HTTP {resp.status_code}: {detail}"}
            data = resp.json()
        except requests.RequestException as e:
            return {"status": "error", "detail": str(e)}
        except ValueError as e:  # JSON 파싱 실패
            return {"status": "error", "detail": f"응답 파싱 실패: {e}"}

        page_items = data.get("items", [])
        for it in page_items:
            title = strip_tags(it.get("title", ""))
            desc = strip_tags(it.get("description", ""))
            link = it.get("link", "")
            items.append({"title": title, "link": link, "description": desc})
            links.extend([link, title, desc])

        # 결과가 더 없으면 다음 페이지 조회 불필요
        if len(page_items) < num:
            break

    return {
        "status": "ok",
        "links": links,
        "items": items,
        "api_meta": {"response_time": response_time,
                     "content_length": content_length},
    }
