# WORK_REPORT — SERP 노출 체크: Custom Search → Serper.dev 전환

## 결론 요약
- 이전 미션에서 도입한 **Google Custom Search JSON API** 방식을 **Serper.dev API**로 교체했다.
  Custom Search는 2025년부터 신규 프로젝트에 접근이 닫혀(호출 시 403) 사용 불가로 확정됐기 때문.
- `serp_checker.check_google_presence(query)` → `POST https://google.serper.dev/search`
  (헤더 `X-API-KEY`, 본문 `{q, gl, hl, num}`). 응답 `organic[].{link,title,snippet}` +
  `knowledgeGraph`를 링크 소스로 반환하고, needle 매칭은 호출측(seo_analyzer)이 수행한다.
- 환경변수를 `GOOGLE_CSE_API_KEY`/`GOOGLE_CSE_CX` → **`SERPER_API_KEY` 하나로** 단순화 (cx 불필요).
- 키 없음/호출 실패 시 0점 대신 `measurable: False`(측정 불가) 유지 — 이전 미션의 동작 그대로.
- owned/profile 로직은 무변경 (HEAD 대비 결과 dict 동일 검증). Custom Search 잔재
  (환경변수·문서·코드 호출)는 모두 제거했고, 남은 "Custom Search" 언급 3곳은 *전환 사유 설명*이다.
- 실키가 없어 Serper 실호출 검증은 불가 — 공식 스키마(`organic[].link/title/snippet`) 기준 mock 테스트로 대체.

## GATE -1 / Phase 0 — 정찰
- clone: 기존 작업 디렉터리(`/home/user/seoblue0342`)가 해당 repo. `HEAD == origin/main`.
- 이전 커밋 확인 (`git log --oneline -5`):
  ```
  06c4f65 feat(serp): 구글 SERP 노출 체크를 스크래핑에서 Google Custom Search API로 교체  ← 걷어낼 대상
  1eda51e Merge: 페이지 유형별 SEO 분석 (권고 노이즈 제거)
  92c13ee feat(seo): 페이지 유형별(직접관리/외부프로필/검색노출) 분석으로 권고 노이즈 제거
  ```
  → 현재 코드는 **Custom Search 버전**임을 확정 (GATE -1 통과).
- remote 주의: 이 환경의 origin은 하네스 프록시(`http://local_proxy@127.0.0.1:.../`)이며
  이를 통해 push가 정상 동작한다. SSH로 바꾸면 프록시 인증이 끊겨 push 실패하므로 **프록시 유지**.
- Custom Search 잔재 위치(전환 전): config.py, serp_checker.py, seo_analyzer.py,
  deploy/README.md, deploy/seoblue0342.service, README.md, tests/test_seo_tool.py, tests/test_serp_checker.py.
- baseline pytest: **29 passed** (수정 전).
- serp 결과 dict 소비자: report_generator(`_html_seo_section`/`_html_menu`/markdown),
  dashboard(`print_seo_analysis`) — `score/passed/total/checks/kind/recommendations/measurable` 읽음.
  webapp/rank_monitor은 serp dict 직접 소비 안 함. (이전 미션에서 이미 확인·구현된 `measurable` 렌더 재사용.)

## Phase 1 — Serper 구현
- `serp_checker.py` 전면 교체: Serper POST 호출, `{status, links, relevance_text, total_results, api_meta}` 반환.
  키 없음 → `no_api_key`, 비200 → `error`(detail에 HTTP코드+메시지). requests만 사용(신규 의존성 없음).
- `seo_analyzer._analyze_serp_google_api`: `check_google_presence(query)` 호출 후
  `links`를 이어붙인 haystack에서 SERP_PRESENCE_TARGETS needle 매칭. 안내 문구를 SERPER_API_KEY 기준으로 교체.
- 다음(Daum) 스크래핑 경로·`measurable=False` 렌더는 이전 미션 그대로 유지(무변경).
- `config.GOOGLE_SEARCH_QUERY` 주석만 Serper로 갱신.
- 테스트: `tests/test_serp_checker.py` 전면 교체(Serper mock 5케이스: 정상/미노출/키없음/403/429),
  `tests/test_seo_tool.py` serp 3케이스(키없음·정상·오류)를 Serper `links` 방식으로 갱신.

## Phase 2 — 배포/문서
- `deploy/seoblue0342.service`: `Environment=SERPER_API_KEY=...` 주석 예시(cx 라인 제거).
- `deploy/README.md`: Serper 키 발급 2단계 + Custom Search 불가 사유 인용.
- `README.md`: 측정 방식 Serper로 갱신 + Custom Search 403 각주(`[^serp]`).

## GATE 검증 결과 → TEST_RESULTS.md
