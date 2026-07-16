# WORK_REPORT — 유튜브 SERP 노출 판정 조건 확대

## 결론 요약
- 구글 SERP 카드의 "유튜브 채널" 미노출은 거짓 음성이었다: needle이 채널 형태
  (`UCQdIJKAOKVI8pKIsvcFBEKA`, `youtube.com/@`)만 매칭해, 실제 노출되는 영상 링크
  (`youtube.com/watch?v=...`)를 놓쳤다.
- `SERP_PRESENCE_TARGETS`의 유튜브 needle에 `"youtube.com/watch"`와 일반 `"youtube.com"`을
  추가해, 채널ID·@handle·개별 영상 어느 형태로 노출되든 "유튜브 노출됨"으로 인정하도록 했다.
- 유튜브 외 타깃(홈페이지·위키·나무위키·교보)과 owned/profile 로직은 무변경 (diff = 유튜브 한 줄 + 주석).

## Phase 0 — 정찰
- 최신 커밋: `3511f5c` (Serper 전환) — 그 위에서 작업. baseline pytest: **31 passed**.
- 수정 전 유튜브 항목 원문 (`seo_analyzer.py`):
  ```python
  ("유튜브 채널", ["UCQdIJKAOKVI8pKIsvcFBEKA", "youtube.com/@"],
   "유튜브 채널명·소개에 '이후 소설가' 키워드를 포함하고 영상을 정기적으로 올리세요."),
  ```
- 유튜브 관련 테스트 단언: 기존 SERP 테스트 픽스처(SERP_HTML, google-api mock links)에는
  youtube 링크가 없어, needle 확대가 기존 단언(위키·교보 노출 / 홈페이지 미노출)에 영향 없음.

## Phase 1 — needle 확대
- 유튜브 needle: `["UCQdIJKAOKVI8pKIsvcFBEKA", "youtube.com/@", "youtube.com/watch", "youtube.com"]`.
- 신규 테스트 `test_serp_youtube_watch_link_counts_as_exposed`:
  Serper links에 `youtube.com/watch?v=...`만 있고 채널ID/@handle이 없어도 유튜브 노출=True,
  동시에 위키·교보는 여전히 미노출(회귀 없음)임을 검증.

## GATE
- (a) 전체 pytest: **32 passed** (baseline 31 + 유튜브-watch 케이스 1건, 신규 실패 0)
- (b) 신규 유튜브-watch 케이스 통과
- (c) 유튜브 외 회귀 없음: `git diff seo_analyzer.py`가 유튜브 항목 한 줄(+설명 주석)만 변경.

## 한계
- 실제 Serper 실호출 검증은 실키 부재로 미수행(공식 스키마 mock으로 대체) — 이전 미션과 동일.
