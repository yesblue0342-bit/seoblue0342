"""
네이버 검색 순위 모니터
- "이후" 키워드로 검색 시 내 페이지들의 순위 확인
- 결과를 SQLite DB에 저장
"""

import sqlite3
import time
import re
from datetime import datetime
from urllib.parse import urlparse, urlencode, unquote

import requests
from bs4 import BeautifulSoup

from config import (
    SEARCH_KEYWORD, MY_PAGES, NAVER_SEARCH_URL,
    HEADERS, DB_PATH, CRAWL_DELAY, MAX_PAGES
)


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """DB 초기화 및 테이블 생성"""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rank_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at  TEXT NOT NULL,
            keyword     TEXT NOT NULL,
            page_name   TEXT NOT NULL,
            rank        INTEGER,
            url_found   TEXT,
            total_results INTEGER
        )
    """)
    conn.commit()
    return conn


def fetch_naver_results(keyword: str, start: int = 1) -> list[dict]:
    """
    네이버 검색 결과 파싱
    Returns: [{"rank": int, "title": str, "url": str, "description": str}, ...]
    """
    params = {
        "where": "web",
        "query": keyword,
        "start": start,
    }
    try:
        resp = requests.get(
            NAVER_SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=10
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [오류] 네이버 요청 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    rank_offset = start  # 1페이지면 1부터, 2페이지면 11부터

    # 네이버 통합/웹 검색 결과 파싱 — 구조가 자주 바뀌므로 다중 셀렉터 폴백
    selector_candidates = [
        "li.bx._svp_item",
        "div.g_item",
        "div.total_wrap li",
        "ul.lst_total > li",
        "div.api_subject_bx li.bx",
        "div.sds-comps-vertical-layout",   # 최신 네이버 통합검색 레이아웃
    ]
    items = []
    for sel in selector_candidates:
        items = soup.select(sel)
        if items:
            break

    if not items:
        # 텍스트 기반 링크 추출 (폴백) — 도메인 단위 중복 제거 + 강화 필터
        # 네이버 구조 변경 시 정식 파싱 실패에 대비한 추정 모드 (정확도 낮음)
        seen_domains = set()
        SKIP_HOSTS = ("naver.com", "naver.net", "pstatic.net", "veta.naver.com", "nstatic")
        idx = 0
        for link in soup.select("a[href]"):
            href = link.get("href", "").strip()
            if not href.startswith("http"):
                continue
            host = urlparse(href).netloc.lower()
            if not host or any(s in host for s in SKIP_HOSTS):
                continue
            # 같은 사이트의 여러 링크는 1개로 (도메인 마지막 2개 레이블 기준)
            base_domain = ".".join(host.split(".")[-2:])
            if base_domain in seen_domains:
                continue
            title = link.get_text(strip=True)
            if len(title) < 4:          # 아이콘/빈 링크 제외
                continue
            seen_domains.add(base_domain)
            results.append({
                "rank": rank_offset + idx,
                "title": title[:80],
                "url": href,
                "description": "",
                "approximate": True,    # 폴백 추정치임을 표시
            })
            idx += 1
        return results[:10]

    for i, item in enumerate(items):
        title_tag = (
            item.select_one("a.link_tit") or
            item.select_one("a.title_link") or
            item.select_one("a[class*='title']") or
            item.select_one("h3 a") or
            item.select_one("a")
        )
        desc_tag = (
            item.select_one("div.dsc_txt") or
            item.select_one("div.total_dsc") or
            item.select_one("p")
        )

        if not title_tag:
            continue

        url = title_tag.get("href", "")
        title = title_tag.get_text(strip=True)
        desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ""

        results.append({
            "rank": rank_offset + i,
            "title": title,
            "url": url,
            "description": desc,
        })

    return results


def check_my_rank(keyword: str = SEARCH_KEYWORD) -> tuple[dict, list, bool]:
    """
    내 페이지들의 현재 순위 확인.
    Returns: (found, all_results, reliable)
        found        = {page_name: {"rank": int|None, "url": str|None, "title": str}, ...}
        all_results  = 수집된 전체 검색 결과 리스트
        reliable     = 네이버 정식 파싱 성공 여부.
                       네이버가 봇 차단/구조 변경으로 정식 셀렉터가 안 맞으면
                       링크 전체를 긁는 폴백으로 빠지는데, 이때 순위 숫자는
                       의미가 없으므로 reliable=False 로 표시하고 순위를 비움.
    """
    print(f"\n🔍 네이버에서 '{keyword}' 검색 중...")

    all_results = []
    for page_num in range(MAX_PAGES):
        start = page_num * 10 + 1
        results = fetch_naver_results(keyword, start=start)
        all_results.extend(results)
        if page_num < MAX_PAGES - 1:
            time.sleep(CRAWL_DELAY)

    print(f"  총 {len(all_results)}개 결과 수집")

    # ── 신뢰도 판정 ──────────────────────────────────────────
    # 정상 네이버 검색은 페이지당 약 10~15개 결과를 돌려준다.
    # 폴백(페이지 내 모든 a 태그 수집)으로 빠지면 페이지당 수십~수백 개가 잡힌다.
    # 평균이 비정상적으로 크면 파싱 실패로 간주.
    avg_per_page = len(all_results) / max(MAX_PAGES, 1)
    reliable = bool(all_results) and avg_per_page <= 18

    # 내 페이지 포함 여부 확인
    found = {name: {"rank": None, "url": None} for name in MY_PAGES}

    for result in all_results:
        url_lower = result["url"].lower()
        for page_name, domain_pattern in MY_PAGES.items():
            pattern_lower = unquote(domain_pattern).lower()
            if (domain_pattern.lower() in url_lower or
                    pattern_lower in unquote(url_lower).lower()):
                if found[page_name]["rank"] is None:  # 첫 번째 매칭만
                    found[page_name] = {
                        "rank": result["rank"],
                        "url": result["url"],
                        "title": result.get("title", ""),
                    }

    # 파싱이 신뢰할 수 없으면 가짜 순위 숫자를 내보내지 않는다
    if not reliable:
        print("  ⚠️ 네이버 정식 파싱 실패(폴백) — 순위 수치는 신뢰 불가로 처리")
        for name in found:
            found[name] = {"rank": None, "url": found[name].get("url"),
                           "note": "네이버 파싱 실패 — 수동 확인 필요"}

    return found, all_results, reliable


def save_rank_result(conn: sqlite3.Connection, keyword: str, 
                     found: dict, total: int):
    """순위 결과 DB 저장"""
    now = datetime.now().isoformat(timespec="seconds")
    rows = []
    for page_name, info in found.items():
        rows.append((
            now, keyword, page_name,
            info.get("rank"), info.get("url"), total
        ))
    conn.executemany(
        "INSERT INTO rank_history "
        "(checked_at, keyword, page_name, rank, url_found, total_results) "
        "VALUES (?,?,?,?,?,?)",
        rows
    )
    conn.commit()


def get_rank_history(conn: sqlite3.Connection, 
                     limit: int = 30) -> list[dict]:
    """최근 순위 히스토리 조회"""
    cursor = conn.execute(
        """SELECT checked_at, keyword, page_name, rank, url_found
           FROM rank_history
           ORDER BY id DESC
           LIMIT ?""",
        (limit,)
    )
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


if __name__ == "__main__":
    conn = init_db()
    found, all_results, reliable = check_my_rank()
    save_rank_result(conn, SEARCH_KEYWORD, found, len(all_results))
    if not reliable:
        print("  ⚠️ (네이버 파싱 신뢰 불가 — 순위 수치 무시)")

    print("\n📊 순위 결과:")
    for name, info in found.items():
        rank = info.get("rank")
        url = info.get("url", "")
        if rank:
            print(f"  [{name}] 순위: {rank}위 | {url[:60]}")
        else:
            print(f"  [{name}] 순위: 상위 {MAX_PAGES*10}위 이내 미발견")
    conn.close()
