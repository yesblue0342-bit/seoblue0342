"""
SERP 노출 체커 — Serper.dev (google.serper.dev) API
- 구글 검색결과 HTML 스크래핑은 봇 차단(동의/축소/JS 셸 페이지)으로 거짓 음성이 나므로,
  서드파티 SERP API인 Serper.dev로 실제 구글 상위 결과를 받아 노출 여부를 판정한다.
- Google Custom Search JSON API는 2025년부터 신규 프로젝트에 닫혀(호출 시 403) 사용 불가라
  종료 리스크가 없고 무료 크레딧(가입 시 2,500회)이 넉넉한 Serper로 전환했다.
- 인증은 환경변수로만 주입 (코드/저장소에 키를 두지 않는다):
    SERPER_API_KEY : serper.dev 대시보드에서 발급한 API 키
  Custom Search와 달리 검색엔진 ID(cx)는 필요 없다.
"""

import os
import time

import requests

SERPER_ENDPOINT = "https://google.serper.dev/search"


def check_google_presence(query: str, num: int = 10) -> dict:
    """Serper.dev로 구글 상위 결과를 받아 링크·텍스트를 반환한다.

    needle 매칭은 호출측(seo_analyzer)에서 수행한다 — 이 모듈은 원천 데이터만 제공.
    Returns (status 별 형태):
      {"status": "no_api_key"}
      {"status": "error", "detail": "..."}
      {"status": "ok", "links": [str, ...], "relevance_text": str,
       "total_results": int, "api_meta": {"response_time": ms, "content_length": bytes}}
    """
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return {"status": "no_api_key"}

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "gl": "kr", "hl": "ko", "num": num}

    try:
        t0 = time.time()
        resp = requests.post(SERPER_ENDPOINT, headers=headers, json=payload, timeout=15)
        response_time = round((time.time() - t0) * 1000)
        content_length = len(resp.content)
        if resp.status_code != 200:
            # 401/403(키 문제)·429(쿼터 초과)·5xx 등 — 부분 결과로 오판하지 않도록 전체 오류 처리
            try:
                detail = resp.json().get("message", "") or resp.text[:200]
            except ValueError:
                detail = resp.text[:200]
            return {"status": "error", "detail": f"HTTP {resp.status_code}: {detail}"}
        data = resp.json()
    except requests.RequestException as e:
        return {"status": "error", "detail": str(e)}
    except ValueError as e:  # JSON 파싱 실패
        return {"status": "error", "detail": f"응답 파싱 실패: {e}"}

    # organic 결과가 주 노출 소스. knowledgeGraph(인물 지식패널)의 링크도 노출로 인정.
    links = []
    relevance_parts = []
    for item in data.get("organic", []):
        for key in ("link", "title", "snippet"):
            val = item.get(key)
            if val:
                links.append(str(val))
        relevance_parts.append(
            f"{item.get('title', '')} {item.get('snippet', '')}")

    kg = data.get("knowledgeGraph") or {}
    for key in ("website", "descriptionLink", "title", "description", "type"):
        val = kg.get(key)
        if val:
            links.append(str(val))
            relevance_parts.append(str(val))

    return {
        "status": "ok",
        "links": links,
        "relevance_text": " ".join(relevance_parts),
        "total_results": len(data.get("organic", [])),
        "api_meta": {"response_time": response_time,
                     "content_length": content_length},
    }
