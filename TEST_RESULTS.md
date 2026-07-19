# TEST_RESULTS — 네이버 순위 → 공식 오픈API 노출 판정

## Baseline (main @ 3eb53f6)
```
python -m pytest tests/ -x -q  →  32 passed
```

## GATE 1
- (a) 전체 pytest: **39 passed** (baseline 32 + naver_checker 7건 + naver 노출 테스트 갱신, 신규 실패 0).
- (b) `tests/test_naver_checker.py` mock 5영역 통과:
  ① 정상 노출(나무위키·유튜브 링크 + 엔드포인트/헤더/파라미터 검증)
  ② 일부 미노출(무관 도메인만 → 타깃 도메인 부재 확인)
  ③ 키 없음(`no_api_key` + GET 요청 0회)
  ④ HTTP 401(Client ID 오류)·429(쿼터 초과) → `status=error`
  ⑤ `<b>` 태그 제거(`strip_tags` + items 태그 제거 확인)
- (c) 키 미설정 시 `check_my_rank('소설가 이후')`:
  ```
  reliable: False | items: 0
  모든 타깃 exposed=None (측정 불가), 거짓 데이터 없음
  note: NAVER_CLIENT_ID/NAVER_CLIENT_SECRET 미설정 — …
  ```
  → 거짓 노출/순위 생성 0, 측정 불가 정직 표시 ✅
- (d) **구글 SERP 회귀 없음:** `git diff HEAD -- serp_checker.py` = 변경 없음.
  수정 전 seo_analyzer(HEAD)와 동일 mock으로 구글 serp 분석 → **결과 dict 완전 동일** ✅

## 통합 렌더 확인 (mock 오픈API 정상 응답)
- `check_my_rank` → 위키/나무위키/유튜브 노출됨, 홈페이지/교보 미노출로 정확 판정.
- HTML 카드: 제목 "네이버 노출 여부", 열 "노출/발견 URL", "✅ 노출됨"·"❌ 미노출" 표시,
  "오픈API 순서 ≠ 통합검색 순위" 안내 포함. '몇 위' 표기 없음.

## FINAL GATE
- pytest: **39 passed** (신규 실패 0)
- 구글 카드 회귀 없음(serp_checker 무변경, 결과 dict 동일)
- 거짓 순위/노출 생성 없음(측정 불가 시 exposed=None)
- 시크릿: `git diff --cached`에 실제 키 패턴 0건, `.env` 미추적
- 문서: README.md / deploy/README.md 갱신(키 3종 목록·네이버 발급 절차)

## 한계
- `NAVER_CLIENT_ID/SECRET` 실키 부재로 오픈API 실호출 검증 미수행 — 미션 제공 검증 스키마
  (`items[].title/link/description`, `<b>` 포함) 기준 mock 테스트로 대체. 서버 키 설정 후
  첫 분석에서 실동작 확인 필요.
