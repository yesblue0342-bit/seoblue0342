# TEST_RESULTS — 유튜브 SERP 노출 판정 조건 확대 (RALPH 미션)

## Baseline (수정 전 main @ 3511f5c)
```
python -m pytest tests/ -x -q  →  31 passed
```

## GATE 1 / FINAL GATE
- (a) 전체 pytest: **32 passed** (baseline 31 + 유튜브-watch 케이스 1건, 신규 실패 0)
- (b) 신규 케이스 `test_serp_youtube_watch_link_counts_as_exposed` 통과:
  Serper links가 `youtube.com/watch?v=1qUVtfqvAwE` / `...=xc2ivmdltmE` 영상 링크만 있고
  채널ID·@handle이 없어도 "검색결과 노출: 유튜브 채널" = True 로 판정.
- (c) 유튜브 외 회귀 없음:
  - 같은 테스트에서 위키백과·교보문고는 여전히 미노출(False) 확인.
  - `git diff seo_analyzer.py` = 유튜브 항목 needle 한 줄 + 설명 주석만 변경.
    다른 SERP 타깃(홈페이지·위키·나무위키·교보)과 owned/profile 로직 무변경.

## 한계
- `SERPER_API_KEY` 실키 부재로 실호출 검증 미수행 — 공식 응답 스키마(`organic[].link`) 기준
  mock 테스트로 대체. 서버 키 설정 후 첫 분석에서 실동작 확인 필요.
