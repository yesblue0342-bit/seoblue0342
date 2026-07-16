# WORK_REPORT — SERP 노출 체크: 스크래핑 → Google Custom Search API 전환

## 결론 요약
- 구글 SERP 노출 체크를 HTML 스크래핑에서 **Google Custom Search JSON API** 호출로 교체했다 (`serp_checker.py` 신규).
- API 키(`GOOGLE_CSE_API_KEY`/`GOOGLE_CSE_CX`) 미설정·호출 실패 시 0점 대신 **"측정 불가"(`measurable: False`)** 상태로 표시해 거짓 음성(0점 왜곡)을 제거했다.
- 다음(Daum) SERP는 스크래핑을 유지하되, 봇 차단 감지 시 기존 결함(권고 문구만 교체하고 checks는 0점 실패로 남던 문제)을 수정해 동일하게 측정 불가 처리한다.
- owned/profile 분석 로직(`_analyze_owned`, `_analyze_profile`)은 수정하지 않았다 (불가침 영역 준수, diff로 확인).
- API 키가 없는 환경이므로 Custom Search API 실호출 검증은 불가 — 공식 응답 스키마(`items[].link/displayLink/snippet`) 기준 mock 단위 테스트로 대체했다 (HARNESS RULE 3에 따라 명시).

## Phase 0 — 정찰 기록

### 기준선 (baseline)
- `python -m pytest tests/ -x -q` → **22 passed** (실패 0건), 커밋 `1eda51e` (main).

### config.py (핵심 원문)
```python
GOOGLE_URL = "https://www.google.com/search?q=%EC%86%8C%EC%84%A4%EA%B0%80%EC%9D%B4%ED%9B%84"
DAUM_URL = "https://search.daum.net/search?w=tot&q=%EC%86%8C%EC%84%A4%EA%B0%80%EC%9D%B4%ED%9B%84"
ANALYSIS_TARGETS = [
    ("이후 공식 홈페이지 (이후.com)", HOMEPAGE_URL, "owned"),
    ...
    ("다음 검색 - 소설가 이후", DAUM_URL, "serp"),
    ("구글 검색 - 소설가 이후", GOOGLE_URL, "serp"),
    ...
]
```

### seo_analyzer.py (수정 전 serp 분기)
```python
if kind == "serp":
    collector = _analyze_serp(soup, url)   # str(soup) 안에 needle grep
    if meta.get("content_length", 0) < 20_000:
        collector.recommendations = ["검색엔진이 봇 요청을 차단했거나 ..."]  # ← checks는 실패로 남음 (결함)
```
- `SERP_PRESENCE_TARGETS`: (이름, needles, 권고) 5건 — 홈페이지/위키백과/나무위키/교보문고/유튜브.
- `_serp_engine_tip(url)`: 도메인별 등록 안내 (google→Search Console 등).

### 결과 dict 소비자 (serp 결과가 흐르는 곳)
- `report_generator._html_seo_section`: `score/passed/total/checks[].{label,passed,value,detail}/recommendations/meta.{status,response_time,content_length}/kind` 사용.
- `report_generator._html_menu`: `score` → 색상 dot.
- `report_generator.generate_markdown_report`: 동일 필드.
- `dashboard.print_seo_analysis`: 동일 필드 + `kind`.
- `webapp.py`: 결과를 직접 읽지 않음 (`run_full_analysis()` → `generate_html_report()` 전달만).
- `rank_monitor.py`: SEO 결과 dict을 전혀 소비하지 않음 (순위 전용).
- `tests/test_seo_tool.py`: serp 관련 기존 테스트 3건
  (`test_serp_kind_checks_exposure_not_meta_tags`, `test_serp_blocked_page_gives_notice_not_false_recs`,
   `test_analysis_targets_have_valid_kinds`) — 구글 URL이 API 경로로 바뀌므로 갱신 필요.

### 환경변수 주입 지점
- `deploy/seoblue0342.service`: `Environment=SEO_DATA_DIR=...` 라인 방식 → 같은 방식으로 주석 예시 추가.
- `deploy/setup-oci.sh`: service 파일을 `/etc/systemd/system/`에 복사·설치 (User 치환만 함).
- `.github/workflows/deploy-oci.yml`: OCI SSH 배포용 시크릿만 사용, 앱 환경변수 주입 없음.
- `.gitignore`: `.env` 항목 없음 → 추가함 (RULE 5).

### 스키마 결정 (측정 불가 표현)
- 결과 dict에 **`"measurable": False`** 필드 추가. 정상 결과는 필드를 넣되 `True`
  (소비자들은 `r.get("measurable", True)`로 읽어 owned/profile 기존 dict과 하위호환).
- `score`는 **정수 0 유지** (None으로 바꾸면 `_score_color(score)` 등 int 연산 소비자가 깨짐 — 최소 침습).
  대신 렌더러가 `measurable=False`면 점수 pill 대신 "⚪ 측정 불가"를 표시하므로 0이 노출되지 않음.
- `checks=[] / passed=0 / total=0` + recommendations에 원인 안내 1건.

## Phase 1 — 구현 기록
- `serp_checker.py` 신규: `check_google_presence(query, needles_map)`
  - `GET https://www.googleapis.com/customsearch/v1?key=...&cx=...&q=...&num=10&gl=kr&hl=ko`
  - 매칭 대상 텍스트 = `items[].link + displayLink + snippet (+ title)`.
  - 기본 1페이지(10건), 미노출 needle이 남아 있을 때만 `start=11`로 2페이지 추가 조회 (쿼터 절약).
  - 반환: `{"status": "no_api_key"}` / `{"status": "error", "detail": ...}` /
    `{"status": "ok", "found": {이름: bool}, "relevance_text": str, "total_results": int, "api_meta": {...}}`
  - 키는 `os.environ.get()`으로만 읽음. requests 외 신규 의존성 없음.
- `seo_analyzer.analyze_seo(kind="serp")`:
  - 구글 URL(호스트에 `google` 포함) → 페이지 fetch 없이 API 사용. `status=="ok"`면 기존과 동일한
    checks 구조(serp_relevance + 노출 5건, 라벨·권고 문구 재사용), 아니면 측정 불가 결과.
  - 다음 등 기타 serp → 기존 스크래핑 유지. `content_length < 20_000`이면 checks 비우고 측정 불가 (결함 수정).
- 렌더러: `measurable=False`면 회색 "⚪ 측정 불가" pill(HTML)/dot(메뉴)/dim 표기(CLI)/마크다운 헤딩.
- `config.py`: `GOOGLE_SEARCH_QUERY = "소설가 이후"` 추가 (GOOGLE_URL은 대시보드 링크용 유지).
- 테스트: `tests/test_serp_checker.py` 신규 (정상 노출/미노출/키 없음/HTTP 429 — mock 4케이스),
  기존 serp 테스트 2건을 새 경로(구글=API, 다음=스크래핑)에 맞게 갱신.

## GATE 검증 결과
→ TEST_RESULTS.md 참조.
