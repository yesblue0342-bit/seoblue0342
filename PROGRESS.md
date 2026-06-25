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
