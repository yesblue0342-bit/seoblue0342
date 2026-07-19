# TEST_RESULTS — 유튜브 분석 대상 Topic → 실제 운영 채널 교체

## Baseline (main @ b2bb72c)
```
python -m pytest tests/ -x -q  →  39 passed
```

## GATE 1 / FINAL GATE
- (a) 전체 pytest: **40 passed** (baseline 39 + 채널 교체 고정 테스트 1건, 신규 실패 0).
- (b) 구글 유튜브 노출 회귀 케이스 유지 확인: `test_serp_youtube_watch_link_counts_as_exposed`
  — 채널ID 없이 `youtube.com/watch?v=...` 링크만 있어도 유튜브 노출=True (그대로 통과).
- (c) **구글 SERP 카드 스냅샷 동일(회귀 없음):** 수정 전 스냅샷과 수정 후 결과가 완전 일치.
  ```
  {"검색결과 관련성 (소설가 이후)": true, "공식 홈페이지": false, "위키백과": false,
   "나무위키": false, "교보문고": false, "유튜브 채널": true}   ← before == after
  ```
- (d) 옛 Topic 채널 ID(`UCQdIJKAOKVI8pKIsvcFBEKA`) 잔재: 코드/설정(`*.py`) 0건.
  WORK_REPORT.md의 경위 설명 언급만 의도적으로 유지.
- 신규 테스트 `test_youtube_target_is_real_operating_channel`: YOUTUBE_URL이 실제 채널ID를
  포함하고 옛 ID를 포함하지 않으며, needle의 일반 `youtube.com`이 유지됨을 고정.

## 네이버 카드 회귀 없음
- `naver_checker.py` 무변경. 네이버 유튜브 판정은 도메인(`youtube.com`) 기반이라 채널ID 교체 영향 없음.

## 채널 검증 (규칙 4)
- 새 채널(`UC3iQTM8DVgzRhgArrSIPp2g`)은 미션 제공 네이버 오픈API 실측 결과 기준: 약 690명 구독,
  동영상 다수 → 실제 운영 채널. title에 "주제/Topic" 없음. (이 환경 네트워크로 직접 title 재확인은
  제한되어 실측 근거로 진행.)

## FINAL GATE 요약
- pytest 40 passed(신규 실패 0), 구글·네이버 카드 회귀 없음, 옛 채널 ID 코드 잔재 0,
  `.env` 미추적, 문서(WORK_REPORT/config 주석) 갱신.
