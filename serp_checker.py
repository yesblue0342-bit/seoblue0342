"""
SERP 노출 체커 — Google Custom Search JSON API
- 구글 검색결과 HTML 스크래핑은 봇 차단(동의/축소/JS 셸 페이지)으로 거짓 음성이 나므로,
  공식 Custom Search API(https://developers.google.com/custom-search/v1/overview)로 대체.
- 인증은 환경변수로만 주입 (코드/저장소에 키를 두지 않는다):
    GOOGLE_CSE_API_KEY : Google Cloud Console에서 발급한 API 키
    GOOGLE_CSE_CX      : programmablesearchengine.google.com 검색엔진 ID
- 무료 쿼터(일 100쿼리)를 고려해 기본 1페이지(10건)만 조회하고,
  미노출 needle이 남아 있을 때만 2페이지(start=11)를 추가 조회한다.
"""

import os
import time

import requests

CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def check_google_presence(query: str, needles_map: dict[str, list[str]],
                          max_pages: int = 2) -> dict:
    """구글 검색결과(상위 10~20건)에서 각 대상의 노출 여부를 API로 확인.

    needles_map: {대상 이름: [매칭 문자열, ...]}
    Returns (status 별 형태):
      {"status": "no_api_key"}
      {"status": "error", "detail": "..."}
      {"status": "ok", "found": {이름: bool}, "relevance_text": str,
       "total_results": int, "api_meta": {"response_time": ms, "content_length": bytes}}
    """
    api_key = os.environ.get("GOOGLE_CSE_API_KEY")
    cx = os.environ.get("GOOGLE_CSE_CX")
    if not api_key or not cx:
        return {"status": "no_api_key"}

    found = {name: False for name in needles_map}
    relevance_parts = []
    total_results = 0
    response_time = 0
    content_length = 0

    for page in range(max_pages):
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": 10,
            "gl": "kr",
            "hl": "ko",
        }
        if page > 0:
            # 2페이지부터는 아직 못 찾은 needle이 있을 때만 조회 (쿼터 절약)
            if all(found.values()):
                break
            params["start"] = page * 10 + 1

        try:
            t0 = time.time()
            resp = requests.get(CSE_ENDPOINT, params=params, timeout=15)
            response_time += round((time.time() - t0) * 1000)
            content_length += len(resp.content)
            if resp.status_code != 200:
                # 429(쿼터 초과)·403(키 문제) 등 — 부분 결과로 오판하지 않도록 전체를 오류 처리
                try:
                    detail = resp.json().get("error", {}).get("message", "")
                except ValueError:
                    detail = resp.text[:200]
                return {"status": "error",
                        "detail": f"HTTP {resp.status_code}: {detail}"}
            data = resp.json()
        except requests.RequestException as e:
            return {"status": "error", "detail": str(e)}
        except ValueError as e:  # JSON 파싱 실패
            return {"status": "error", "detail": f"응답 파싱 실패: {e}"}

        items = data.get("items", [])
        total_results += len(items)
        for item in items:
            haystack = " ".join(str(item.get(k, "")) for k in
                                ("link", "displayLink", "snippet", "title"))
            relevance_parts.append(
                f"{item.get('title', '')} {item.get('snippet', '')}")
            for name, needles in needles_map.items():
                if not found[name] and any(n in haystack for n in needles):
                    found[name] = True

        if not items:  # 결과가 더 없으면 다음 페이지 조회 불필요
            break

    return {
        "status": "ok",
        "found": found,
        "relevance_text": " ".join(relevance_parts),
        "total_results": total_results,
        "api_meta": {"response_time": response_time,
                     "content_length": content_length},
    }
