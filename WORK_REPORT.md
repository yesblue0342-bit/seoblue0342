# WORK_REPORT — 유튜브 분석 대상: Topic 채널 → 실제 운영 채널 교체

## 결론 요약 (최신 미션)
- 유튜브 카드가 평가하던 대상이 실제 운영 채널이 아니라 유튜브가 음원 유통으로 자동 생성한
  **Topic("주제") 채널**(`UCQdIJKAOKVI8pKIsvcFBEKA`)이었다. Topic 채널은 소개글·정보란이 없어
  메타 디스크립션 등 3개 항목이 원리적으로 개선 불가 → 잘못된 대상을 측정하던 상태.
- `config.YOUTUBE_URL`과 `seo_analyzer` 유튜브 needle의 채널 ID를 네이버 오픈API로 실측 확인된
  **실제 운영 채널**(`UC3iQTM8DVgzRhgArrSIPp2g`, 약 690명 구독·동영상 다수)로 교체했다.
- 구글 SERP 회귀 방지: 유튜브 needle의 일반 `youtube.com`·`youtube.com/@`·`youtube.com/watch`는
  그대로 두어, 채널 ID를 바꿔도 구글 카드 판정이 동일함을 **스냅샷 비교**로 보증(100점 유지).
- `serp_checker.py`·`naver_checker.py`·owned/profile 로직은 불가침(무변경). 옛 채널 ID는 코드/설정에서
  제거하고 WORK_REPORT의 경위 설명 목적 언급만 유지.
- 채널 검증: 네트워크로 새 채널 title 직접 확인은 이 환경에서 제한되나, 미션에 제공된 네이버
  오픈API 실측(구독자·동영상 수 있는 실제 채널, title에 "주제/Topic" 없음)을 근거로 진행.

---

## 결론 요약 (이전 미션 — 네이버 순위 → 공식 오픈API 노출 판정)
- 네이버 카드가 스크래핑 봇 차단으로 전 항목 "파싱 실패"로만 뜨던 문제를, 네이버 **공식 오픈API
  (webkr)** 호출로 교체해 해결했다 (`naver_checker.py` 신규).
- **'순위'를 포기하고 '노출 여부'로 전환**했다: 오픈API 결과 순서는 통합검색 화면 순위와
  일치하지 않아 '몇 위'는 거짓 정보다. 구글 SERP 카드와 동일하게 각 타깃의 노출 O/X + 발견 URL만 표시.
- 키(`NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`) 미설정·호출 실패 시 거짓 데이터를 만들지 않고
  '측정 불가'로 정직하게 표시(기존 정직성 UX 유지·강화). 스크래핑 폴백(추정 순위)은 완전 제거.
- 구글 SERP(`serp_checker.py`·`SERP_PRESENCE_TARGETS`)와 owned/profile 로직은 1바이트도 안 바꿨다
  (HEAD 대비 구글 결과 dict 동일 검증).
- **사용자 조치:** 호스트 `/opt/seoblue0342/.env`에 `NAVER_CLIENT_ID`·`NAVER_CLIENT_SECRET` 추가
  (SERPER_API_KEY와 함께). Docker 배포 시 자동 주입.
- 실키 부재로 오픈API 실호출 검증은 미수행 — 미션에 제공된 검증된 스키마(`items[].title/link/description`,
  `<b>` 태그 포함) 기준 mock 테스트로 대체.

## Phase 0 — 정찰
- 최신 커밋: `3eb53f6`(run-docker .env 주입). baseline pytest: **32 passed**.
- 유튜브 채널 ID 불일치 기록: 실호출 확인값 `UC3iQTM8DVgzRhgArrSIPp2g` vs
  `config.YOUTUBE_URL`의 `UCQdIJKAOKVI8pKIsvcFBEKA`. **판단:** 네이버 판정은 도메인(`youtube.com`)
  기반 매칭이라 채널 ID 불일치의 영향을 받지 않는다. 구글 카드도 needle에 일반 `youtube.com`이 있어
  통과 중. 따라서 이번 미션 범위에서 YOUTUBE_URL 값은 **교체하지 않는다**(불가침 최소침습 원칙 +
  값 교체는 별도 확인이 필요한 사안). 사실만 기록.
  - **[후속 처리]** 이 보류 항목은 다음 미션(Topic→실제 운영 채널 교체)에서 처리됨.
    `YOUTUBE_URL`과 seo_analyzer 유튜브 needle의 옛 Topic 채널 ID(`UCQdIJKAOKVI8pKIsvcFBEKA`)를
    실제 운영 채널 ID(`UC3iQTM8DVgzRhgArrSIPp2g`)로 교체. 구글 needle의 일반 `youtube.com`은 유지해
    회귀 없음(스냅샷 비교로 보증). 상세는 이 파일 최상단 결론 요약 참조.
- 순위 개념 의존부: `rank_monitor.fetch_naver_results`(스크래핑·추정 순위), `check_my_rank`(순위 계산),
  `report_generator._html_rank_section`/markdown, `dashboard.print_rank_results`가 rank에 의존.
  `webapp.py`는 `check_my_rank`→`save_rank_result`→튜플 전달만(순위 로직 없음).
- DB: `rank_history(rank INTEGER, url_found TEXT, ...)`. **결정:** 스키마·`save_rank_result`·
  `get_rank_history` 시그니처 무변경(최소 침습). 새 found엔 rank 키가 없어 `info.get("rank")`→NULL 저장,
  노출은 `url_found`(비어있지 않으면 노출)로 자연 기록됨.
- 스키마 결정(측정 불가 표현): 구글 `measurable` 패턴과 일관되게, `check_my_rank`의 3-튜플
  `(found, all_results, reliable)`을 유지하되 의미를 재정의 — `reliable`=측정 성공 여부,
  `found[name]={"exposed": bool|None, "url": str|None, "note"?: str}`. exposed=None → 측정 불가.

## Phase 1 — 구현
- `naver_checker.check_naver_presence(query)`: `GET .../webkr.json`, 헤더 X-Naver-Client-Id/Secret,
  `{query, display:10, start}`. 응답 `items[]`의 link + 태그 제거한 title/description을 links로 수집.
  `strip_tags()`로 `<b>` 등 제거. no_api_key/error/ok 상태. 1페이지 후 결과가 display 미만이면 중단(호출 절약).
- `rank_monitor`: `fetch_naver_results`(스크래핑·폴백 추정) **삭제**. `check_my_rank`가
  `NAVER_PRESENCE_TARGETS`(홈페이지·위키·나무위키·교보·유튜브, 도메인 needle) 각각에 대해
  items에서 도메인 매칭으로 노출 O/X + URL 판정. 실패 시 exposed=None + note.
  검색결과 페이지(search.naver.com·search.daum.net)는 webkr에 안 잡혀 항상 미노출로 오판되므로 타깃 제외.
- 렌더러: HTML/마크다운/CLI 모두 열 이름 `순위`→`노출`, 카드 제목 "네이버 노출 여부",
  "오픈API 순서≠통합검색 순위" 1줄 안내 추가. 측정 불가는 회색 표기 + 원인 note.
- `config.NAVER_SEARCH_QUERY = "소설가 이후"` 추가.

## Phase 2 — 배포/문서
- `deploy/run-docker.sh`는 이미 `.env` 자동 주입 → 구조 변경 없음. `deploy/README.md`에 필요한
  키 3종(SERPER_API_KEY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET) 목록과 네이버 발급 절차 문서화.
- `README.md`: 네이버 측정 방식(스크래핑→오픈API), 노출 여부인 이유, 환경변수 2개 추가.

## GATE 검증 → TEST_RESULTS.md
