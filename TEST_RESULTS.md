# TEST_RESULTS — SERP API 전환 (RALPH 미션)

## Baseline (Phase 0, 수정 전 main @ 1eda51e)
```
python -m pytest tests/ -x -q  →  22 passed  (실패 0건)
```

## GATE 1
- (a) 전체 pytest: **29 passed** (baseline 22 → serp 테스트 2건 갱신, 신규 7건 추가, 신규 실패 0건)
- (b) `tests/test_serp_checker.py` mock 4케이스 통과:
  ① 정상 노출(1페이지에서 전부 발견 → API 1회만 호출)
  ② 미노출(2페이지 `start=11` 추가 조회 확인)
  ③ 키 없음(`no_api_key` + 네트워크 요청 0회)
  ④ HTTP 429(쿼터 초과 → `status=error`, detail에 코드·메시지)
- (c) 키 미설정 CLI 확인:
  ```
  measurable: False | checks: 0 | score: 0 / 0
  rec: GOOGLE_CSE_API_KEY 미설정: Google Cloud Console에서 Custom Search API 키와 검색엔진 ID(cx)를…
  ```
  → measurable=False, 실패 체크 0건, 안내 권고 1건 ✅
- (d) owned/profile 회귀 검증: 수정 전 코드(`git show HEAD:seo_analyzer.py`)를 별도 모듈로 로드해
  동일한 mock HTML로 실행, **결과 dict 완전 동일** (owned 60점 9/15, profile 50점 3/6) ✅

## FINAL GATE
- pytest 전체: 29 passed (신규 실패 0)
- 시크릿 grep: `git diff --cached | grep -iE "AIza|api_key.*=.*['\"][A-Za-z0-9]"` → 0건
- `.env` .gitignore 등재 확인
- README.md / deploy/README.md / deploy/seoblue0342.service 문서·주석 갱신
- measurable=False 렌더: HTML·마크다운 리포트에 "측정 불가" 표시, "0점" 미출력 (테스트 `test_unmeasurable_renders_as_no_score`)

## 한계 (명시)
- `GOOGLE_CSE_API_KEY` 실키가 없는 환경이라 Custom Search API **실호출 검증은 미수행** —
  공식 응답 스키마(`items[].link/displayLink/snippet/title`) 기준 mock 테스트로 대체.
  서버에 키 설정 후 첫 분석에서 실동작 확인 필요.
