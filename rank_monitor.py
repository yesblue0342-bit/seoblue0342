"""
네이버 노출 모니터
- 네이버 공식 오픈API(webkr)로 '소설가 이후' 검색 시 내 페이지들의 노출 여부 확인
- 결과를 SQLite DB에 저장

※ '순위'가 아니라 '노출 여부'다: 오픈API 결과 순서는 통합검색 화면 순위와 일치하지 않으므로
  거짓 순위를 만들지 않고 각 타깃의 노출 O/X + 발견 URL만 다룬다.
"""

import sqlite3
from datetime import datetime

import naver_checker
from config import (
    SEARCH_KEYWORD, NAVER_SEARCH_QUERY, DB_PATH,
)


# 네이버 검색결과에서 노출 여부를 확인할 타깃 (표시명, 도메인 needle 목록).
# 구글 SERP_PRESENCE_TARGETS 와 별개 상수 — 구글 쪽은 건드리지 않는다.
# search.naver.com·search.daum.net 같은 검색결과 페이지는 webkr 웹문서에 잡히지 않아
# 항상 미노출로 오판되므로 타깃에서 제외(정직성 유지).
NAVER_PRESENCE_TARGETS = [
    ("공식 홈페이지 (이후.com)", ["xn--hu5b23z.com"]),
    ("위키백과 문서", ["ko.wikipedia.org"]),
    ("나무위키 문서", ["namu.wiki"]),
    ("교보문고 작가 페이지", ["kyobobook.co.kr"]),
    ("유튜브 채널", ["youtube.com"]),
]


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


def check_my_rank(keyword: str = SEARCH_KEYWORD) -> tuple[dict, list, bool]:
    """
    내 페이지들의 네이버 검색 노출 여부 확인 (공식 오픈API).

    Returns: (found, all_results, reliable)
        found        = {표시명: {"exposed": bool|None, "url": str|None, "note"?: str}, ...}
                       exposed=True 노출됨 / False 미노출 / None 측정 불가
        all_results  = 오픈API가 돌려준 항목 리스트 (측정 불가 시 빈 리스트)
        reliable     = 측정 성공 여부(=measurable). 키 미설정/호출 실패면 False 로 두고
                       거짓 노출 데이터를 만들지 않는다(정직한 실패 UX 유지).

    ※ '순위'가 아니라 '노출 여부'만 판정한다 (오픈API 순서 ≠ 통합검색 순위).
    """
    print(f"\n🔍 네이버 오픈API로 '{NAVER_SEARCH_QUERY}' 노출 확인 중...")

    api = naver_checker.check_naver_presence(NAVER_SEARCH_QUERY)

    if api["status"] != "ok":
        if api["status"] == "no_api_key":
            note = ("NAVER_CLIENT_ID/NAVER_CLIENT_SECRET 미설정 — 네이버 개발자센터에서 "
                    "검색 오픈API 애플리케이션을 등록해 키를 발급하고 환경변수로 설정하세요.")
        else:
            note = f"네이버 오픈API 호출 실패: {api.get('detail', '알 수 없는 오류')}"
        print(f"  ⚠️ 측정 불가 — {note}")
        found = {name: {"exposed": None, "url": None, "note": note}
                 for name, _ in NAVER_PRESENCE_TARGETS}
        return found, [], False

    items = api["items"]
    print(f"  총 {len(items)}개 결과 수집")

    found = {}
    for name, needles in NAVER_PRESENCE_TARGETS:
        matched_url = None
        for it in items:
            haystack = f"{it.get('link','')} {it.get('title','')} {it.get('description','')}".lower()
            if any(n.lower() in haystack for n in needles):
                matched_url = it.get("link") or matched_url
                break
        found[name] = {"exposed": bool(matched_url), "url": matched_url}

    return found, items, True


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
        print("  ⚠️ (네이버 오픈API 측정 불가 — 노출 여부 판정 생략)")

    print("\n📊 네이버 노출 여부:")
    for name, info in found.items():
        exposed = info.get("exposed")
        url = info.get("url") or ""
        if exposed is None:
            print(f"  [{name}] 측정 불가")
        elif exposed:
            print(f"  [{name}] ✅ 노출 | {url[:60]}")
        else:
            print(f"  [{name}] ❌ 미노출")
    conn.close()
