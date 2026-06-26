# PROGRESS

## 가정 및 결정사항
- 네이버 검색 결과를 직접 스크래핑하는 방식 사용 (robots.txt 준수, 헤더 적절히 설정)
- Playwright 대신 requests+BeautifulSoup 사용 (경량화)
- 홈페이지 도메인 xn--hu5b23z.com = "이후.com" (퓨니코드)
- 순위 히스토리는 SQLite로 로컬 저장
- SEO 리포트는 HTML+터미널 양방향 출력
- 배포 자산(deploy/)의 인물 정보는 공개 자료 기준 초안 — 실제 프로필에 맞게 수정 전제

## 수정 내역 (260625)
- [버그] main.py가 import하는 report_generator.py 부재 → 신규 작성 (실행 즉시 ImportError 해결)
- [버그] config.py Accept 헤더 application/xhtml+xml 중복 → 정리
- [버그] seo_analyzer.py fetch 실패 반환 dict에 passed/total 누락 →
         네트워크 오류 시 dashboard KeyError 전체 크래시 발생하던 것 수정
- [개선] rank_monitor.py 네이버 셀렉터 다중 폴백 보강, 폴백 링크에서 광고/내부 도메인 제외
- [개선] check_my_rank 반환 타입힌트/docstring을 실제 tuple 반환에 맞게 정정
- [정리] dashboard.py 미사용 import 제거
- [문서] CLAUDE.md 위키백과 URL 깨진 퍼센트 인코딩 수정

## 배포 자산 (deploy/)
- head-snippet.html : 홈페이지 <head>용 메타태그+JSON-LD 일괄 블록
- structured-data.jsonld : Person/Book 스키마 (분리 관리용)
- sitemap.xml / robots.txt : 루트 업로드용 (네이버 Yeti·구글봇 허용)

## 추가 개선 (260625 오후)
- [개선] 순위 파서 정직화: 폴백(파싱 실패) 감지 → 가짜 순위 숫자 대신 "측정 불가" 표시
         (페이지당 결과 수가 비정상적으로 많으면 reliable=False)
- [기능] webapp 매일 자동 분석 스케줄러 추가 (APScheduler, 기본 새벽 4시 KST, 하루 1회)
         네이버 차단 위험 줄이려 보수적으로 1회/일
- [배포] Dockerfile 워커 1개로 (스케줄러 중복 실행 방지)
- check_my_rank 반환 (found, all_results) → (found, all_results, reliable) 3-tuple
- 리포트(HTML/MD)에 신뢰불가 경고 배너 + '이후 소설가' 직접검색 권장 추가

## 모바일 레이아웃 수정 (260626 3차)
- [버그] 셸 헤더(.bar)가 비-wrap flex 행이라 모바일에서 긴 제목이 한 글자씩 세로로 깨짐
         → flex-wrap + 모바일 미디어쿼리(제목 전체폭, 메타/버튼 2행 배치)로 수정.
- [개선] body flex-column + iframe flex:1 로 변경(고정 calc(100vh-50px) 제거) — 헤더 높이 변동에도 안정.
- [개선] 리포트(report_generator) 모바일 미디어쿼리 추가(hero/card/table/menu 패딩·폰트 축소).
- [주의] 위 수정은 webapp.py(셸)·report_generator.py(리포트) 코드 변경 → OCI 컨테이너 재빌드 필요.
         자동배포 시크릿 미등록 상태면 라이브 미반영(아래 2차 항목 참조).

## 정보 소스 확장 + OCI 자동배포 (260626 2차)
- [기능] 다음(Daum) 검색 소스 추가 → 총 7개 (홈페이지·위키백과·나무위키·다음·구글·교보문고·유튜브).
- [배포] OCI 자동배포 부재로 1차 커밋이 라이브에 안 보였던 문제 → deploy-oci.yml 추가.
         main push 시 OCI 서버 SSH → git reset --hard + run-docker.sh 재빌드 → /refresh 분석 갱신.
         OCI_SSH_* 시크릿 미설정 시 graceful skip(green). stella-ai-workspace 패턴 재사용.
- [가정] OCI 배포 시크릿 이름은 stella-ai-workspace 와 동일(OCI_SSH_HOST/USER/KEY/PORT, OCI_APP_DIR)
         으로 통일. 이 레포에 미등록이면 Settings→Secrets 에 동일 이름으로 등록 시 자동 배포됨.

## 정보 소스 확장 (260626)
- [기능] 대시보드 분석 대상에 나무위키·교보문고·구글·유튜브 추가.
         단일출처 config.ANALYSIS_TARGETS 에 (라벨, URL)로 정의 → seo_analyzer.run_full_analysis 가
         그대로 순회. 카드·상단 메뉴·일일 자동 배치잡(스케줄러) 모두 자동 반영됨.
- [기능] 리포트 상단에 정보 소스 점프 메뉴(nav.menu, 점수색 점) + 각 카드 앵커(id=src-N) 추가
         → "대시보드에 메뉴가 없다"는 요청 해결.
- [가정] 구글/유튜브 외부 페이지는 봇 차단·JS 렌더로 fetch 실패할 수 있음 → 기존 graceful 처리로
         "접근 불가" 카드로 표시(크래시 없음). 메뉴/카드 노출 목적은 충족.
- [가정] MY_PAGES 에도 namu/kyobo/youtube 추가 → 네이버 순위 모니터가 해당 도메인 노출도 추적.
- [테스트] 신규 4건 추가, pytest 총 17 passed.

## 홈페이지(Leehu) SEO — GitHub Pages 유지
- SEO 메타/OG/JSON-LD는 커밋 ad57da8에서 이미 적용 완료 (47점→대폭 개선 예상)
- robots.txt/sitemap.xml NULL 바이트 손상 → 정상 파일로 복구 (커밋 4c6ed65)
- og-image.jpg(1200x630) 생성 추가 (OG 404 해결)
