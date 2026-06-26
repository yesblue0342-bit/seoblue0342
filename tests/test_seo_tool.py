"""
자동화 테스트 (총 13개)
- 네트워크 요청 없이 순수 로직 / 산출물만 검증 (CI에서 안정적으로 통과)
실행: pytest -q  (또는 python -m pytest)
"""

import json
import os
import sys

# 상위 디렉토리 모듈 import 가능하도록 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import report_generator as rg
from rank_monitor import init_db, save_rank_result, get_rank_history
from seo_analyzer import analyze_seo, SEO_CHECKS


# ── 목 데이터 ────────────────────────────────────────────────
MOCK_ANALYSIS = [{
    "label": "테스트 페이지",
    "url": "https://example.com",
    "meta": {"status": 200, "response_time": 100, "content_length": 10240},
    "checks": [
        {"key": "title", "label": "Title", "passed": True, "value": "제목", "detail": ""},
        {"key": "structured_data", "label": "JSON-LD", "passed": False,
         "value": "", "detail": "구조화 데이터 추가 필요"},
    ],
    "score": 50, "passed": 1, "total": 2,
    "recommendations": ["[JSON-LD] 구조화 데이터 추가 필요"],
}]
MOCK_RANK = (
    {"homepage": {"rank": 3, "url": "https://xn--hu5b23z.com/", "title": "이후"}},
    [{"rank": 1}, {"rank": 2}, {"rank": 3}],
)


# ── 1. config 무결성 ─────────────────────────────────────────
def test_config_keyword():
    assert config.SEARCH_KEYWORD == "이후"


def test_config_homepage_punycode():
    # 이후.com 의 퓨니코드
    assert config.HOMEPAGE_URL.startswith("https://xn--hu5b23z.com")


def test_config_my_pages_keys():
    assert set(["naver_profile", "wikipedia", "homepage"]).issubset(config.MY_PAGES.keys())


def test_config_extra_sources_present():
    # 나무위키·교보문고·구글·유튜브 정보 소스 URL 정의 존재
    assert config.NAMU_URL.startswith("https://namu.wiki/")
    assert "kyobobook.co.kr" in config.KYOBO_URL
    assert config.GOOGLE_URL.startswith("https://www.google.com/")
    assert "youtube.com" in config.YOUTUBE_URL


def test_analysis_targets_cover_all_sources():
    # 대시보드 분석 대상(=카드/메뉴)에 6개 정보 소스가 모두 포함돼야 함
    urls = [u for _, u in config.ANALYSIS_TARGETS]
    for u in (config.HOMEPAGE_URL, config.WIKIPEDIA_URL, config.NAMU_URL,
              config.KYOBO_URL, config.GOOGLE_URL, config.YOUTUBE_URL):
        assert u in urls
    assert len(config.ANALYSIS_TARGETS) >= 6


def test_run_full_analysis_uses_targets(monkeypatch):
    # run_full_analysis 가 ANALYSIS_TARGETS 를 그대로 순회하는지 (네트워크 없이 검증)
    import seo_analyzer
    seen = []

    def fake_analyze(url, label):
        seen.append((label, url))
        return {"label": label, "url": url, "meta": {}, "checks": [],
                "score": 0, "passed": 0, "total": 0, "recommendations": []}

    monkeypatch.setattr(seo_analyzer, "analyze_seo", fake_analyze)
    monkeypatch.setattr(seo_analyzer.time, "sleep", lambda *_: None)
    results = seo_analyzer.run_full_analysis()
    assert len(results) == len(config.ANALYSIS_TARGETS)
    labels = [lbl for lbl, _ in seen]
    assert any("나무위키" in l for l in labels)
    assert any("교보문고" in l for l in labels)
    assert any("구글" in l for l in labels)
    assert any("유튜브" in l for l in labels)


def test_html_report_has_source_menu(tmp_path):
    # 리포트 상단에 정보 소스 점프 메뉴(nav.menu)와 카드 앵커가 있어야 함
    multi = [
        {"label": "나무위키 - 이후(소설가)", "url": "https://namu.wiki/x",
         "meta": {"status": 200}, "checks": [], "score": 80, "passed": 0,
         "total": 0, "recommendations": []},
        {"label": "교보문고 - 작가 이후", "url": "https://store.kyobobook.co.kr/x",
         "meta": {"status": 200}, "checks": [], "score": 30, "passed": 0,
         "total": 0, "recommendations": []},
    ]
    out = tmp_path / "menu.html"
    rg.generate_html_report(multi, None, str(out))
    html = out.read_text(encoding="utf-8")
    assert "class='menu'" in html or 'class="menu"' in html
    assert "#src-0" in html and "#src-1" in html
    assert 'id="src-0"' in html and 'id="src-1"' in html
    assert "나무위키" in html and "교보문고" in html


def test_config_headers_no_duplicate_accept():
    # Accept 헤더에 동일 MIME 중복이 없어야 함 (수정된 버그)
    accept = config.HEADERS["Accept"]
    assert accept.count("application/xhtml+xml") == 1


# ── 2. SEO 체크 항목 정의 ────────────────────────────────────
def test_seo_checks_count():
    # 메타/OG/JSON-LD 등 핵심 항목 정의 존재
    assert len(SEO_CHECKS) >= 13
    assert "structured_data" in SEO_CHECKS


# ── 3. 리포트 생성기 (HTML) ──────────────────────────────────
def test_html_report_created(tmp_path):
    out = tmp_path / "r.html"
    path = rg.generate_html_report(MOCK_ANALYSIS, MOCK_RANK, str(out))
    assert os.path.exists(path)
    html = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "테스트 페이지" in html
    assert "JSON-LD" in html


# ── 4. 리포트 생성기 (Markdown) ──────────────────────────────
def test_markdown_report_created(tmp_path):
    out = tmp_path / "r.md"
    path = rg.generate_markdown_report(MOCK_ANALYSIS, MOCK_RANK, str(out))
    md = out.read_text(encoding="utf-8")
    assert md.startswith("#")
    assert "테스트 페이지" in md


# ── 5. 리포트 생성기: rank_results=None 도 안전 ──────────────
def test_report_handles_none_rank(tmp_path):
    out = tmp_path / "r2.html"
    rg.generate_html_report(MOCK_ANALYSIS, None, str(out))
    assert out.exists()


# ── 6. 점수 색상 로직 ────────────────────────────────────────
def test_score_color_thresholds():
    assert rg._score_color(80) == "#16a34a"   # 양호
    assert rg._score_color(50) == "#d97706"   # 보통
    assert rg._score_color(20) == "#dc2626"   # 미흡


# ── 7. DB 저장/조회 라운드트립 ───────────────────────────────
def test_db_roundtrip(tmp_path):
    db = tmp_path / "t.db"
    conn = init_db(str(db))
    found = {"homepage": {"rank": 5, "url": "https://xn--hu5b23z.com/"}}
    save_rank_result(conn, "이후", found, total=50)
    history = get_rank_history(conn)
    assert len(history) == 1
    assert history[0]["page_name"] == "homepage"
    assert history[0]["rank"] == 5
    conn.close()


# ── 8. 구조화 데이터 JSON 유효성 ─────────────────────────────
def test_structured_data_valid_json():
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "deploy", "structured-data.jsonld",
    )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)          # 깨진 JSON이면 여기서 실패
    graph = data["@graph"]
    persons = [n for n in graph if n.get("@type") == "Person"]
    assert persons and persons[0]["name"] == "이후"


# ── 9. 회귀: 페이지 접근 실패 결과도 크래시 없이 처리 ────────
def test_failed_fetch_result_is_renderable(tmp_path):
    """fetch 실패 시 반환되는 dict(passed/total 포함)가
    dashboard / report 에서 KeyError 없이 처리돼야 함 (수정된 크래시 버그)."""
    failed = {
        "label": "접근 불가 페이지", "url": "https://x.invalid",
        "meta": {"error": "연결 실패"}, "checks": [],
        "score": 0, "passed": 0, "total": 0,
        "recommendations": ["페이지 접근 불가: 연결 실패"],
    }
    # passed/total 키가 존재해야 함
    assert "passed" in failed and "total" in failed
    # 리포트 생성기에서 예외 없이 처리
    out = tmp_path / "fail.html"
    rg.generate_html_report([failed], None, str(out))
    assert out.exists()
    # dashboard 출력도 예외 없이 처리
    from dashboard import print_seo_analysis
    print_seo_analysis([failed])


# ── 10. 순위 신뢰도: 파싱 실패 시 가짜 순위 숨김 ────────────
def test_rank_reliability_hides_fake_rank():
    """폴백(파싱 실패) 시 가짜 순위 숫자 대신 '측정 불가' 표시."""
    found = {"homepage": {"rank": None, "url": "https://xn--hu5b23z.com/",
                          "note": "네이버 파싱 실패 — 수동 확인 필요"}}
    # reliable=False (3-tuple)
    html = rg._html_rank_section((found, list(range(349)), False))
    assert "신뢰할 수 없" in html        # 경고 배너
    assert "측정 불가" in html or "수동 확인" in html

    # reliable=True 일 때는 순위 정상 표시
    ok = {"homepage": {"rank": 5, "url": "https://xn--hu5b23z.com/"}}
    html2 = rg._html_rank_section((ok, list(range(50)), True))
    assert "5위" in html2

    # 2-tuple 하위호환 (reliable 생략 → True 취급)
    html3 = rg._html_rank_section((ok, list(range(50))))
    assert "5위" in html3
