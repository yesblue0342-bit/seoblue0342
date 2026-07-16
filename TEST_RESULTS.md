# TEST_RESULTS — Custom Search → Serper.dev 전환 (RALPH 미션)

## Baseline (Phase 0, 수정 전 main @ 06c4f65 = Custom Search 버전)
```
python -m pytest tests/ -x -q  →  29 passed  (실패 0건)
```

## GATE 1
- (a) 전체 pytest: **31 passed** (baseline 29 → serp 테스트 갱신 + 오류 케이스 1건 추가, 신규 실패 0건)
- (b) `tests/test_serp_checker.py` Serper mock 5케이스 통과:
  ① 정상 노출(엔드포인트=google.serper.dev/search, X-API-KEY 헤더, q 본문 검증 + 링크 매칭)
  ② 미노출(대상 도메인 부재 확인)
  ③ 키 없음(`no_api_key` + POST 요청 0회)
  ④ HTTP 403(키 문제 → `status=error`, detail에 403·Unauthorized)
  ⑤ HTTP 429(쿼터 초과 → `status=error`, detail에 429)
- (c) 키 미설정 CLI 확인:
  ```
  measurable: False | checks: 0 | score: 0
  rec: SERPER_API_KEY 미설정: serper.dev에 가입해 API 키를 발급받아 환경변수(SERPER_API_KEY)로 …
  ```
  → measurable=False, 실패 체크 0건, 안내 권고 1건 ✅
- (d) owned/profile 회귀: 수정 전 코드(`git show HEAD:seo_analyzer.py`)와 동일 mock HTML 비교 →
  **결과 dict 완전 동일** (owned 60점 9/15, profile 50점 3/6) ✅

## FINAL GATE
- pytest 전체: **31 passed** (신규 실패 0)
- 시크릿 grep: `git diff --cached | grep -iE "serper.*[0-9a-f]{40}|X-API-KEY.*[0-9a-f]"` → 0건
- `.env` .gitignore 등재 확인 (이전 미션에서 추가됨)
- Custom Search 잔재 제거 확인: 활성 코드/설정에서 `GOOGLE_CSE`·`customsearch`·cx 0건.
  남은 "Custom Search" 문자열 3곳(serp_checker docstring, README 각주, deploy/README 인용)은
  **전환 사유 설명**으로 의도적 유지.
- README.md / deploy/README.md / deploy/seoblue0342.service 문서·주석 갱신
- measurable=False 렌더: HTML·마크다운 "측정 불가" 표시(테스트 `test_unmeasurable_renders_as_no_score`)

## 한계 (명시)
- `SERPER_API_KEY` 실키가 없는 환경이라 Serper.dev **실호출 검증은 미수행** —
  공식 응답 스키마(`organic[].link/title/snippet`, `knowledgeGraph`) 기준 mock 테스트로 대체.
  서버에 키 설정 후 첫 분석에서 실동작 확인 필요.
