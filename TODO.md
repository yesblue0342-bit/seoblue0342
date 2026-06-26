# TODO

- [x] 1. 프로젝트 구조 및 의존성 설정
- [x] 2. 네이버 검색 순위 모니터 구현
- [x] 3. 페이지 SEO 분석기 구현
- [x] 4. 홈페이지 SEO 자동 개선 권고 리포트 생성
- [x] 5. CLI 대시보드 (rich) 구현
- [x] 6. 순위 히스토리 DB 저장/조회
- [x] 7. 전체 테스트 및 실행 확인

## 추가 완료 (정보 소스 확장 · 260626)
- [x] 정보 소스에 나무위키·다음·교보문고·구글·유튜브 추가 (config.ANALYSIS_TARGETS 단일출처, 총 7개)
- [x] run_full_analysis 가 ANALYSIS_TARGETS 순회 → 카드/일일 배치잡 자동 반영
- [x] 대시보드 상단 정보 소스 점프 메뉴(nav.menu) + 카드 앵커 추가
- [x] OCI 자동배포 워크플로(deploy-oci.yml) 추가 — push 시 재빌드+/refresh, 시크릿 없으면 graceful skip
- [x] 신규 테스트 4건 추가 (소스 URL·타겟·메뉴 렌더 검증) — pytest 17 passed

## 추가 완료 (정리/배포)
- [x] 누락 모듈 report_generator.py 작성 (HTML/MD 리포트)
- [x] 소스 버그 수정 (Accept 헤더 중복, fetch 실패 KeyError 크래시, 셀렉터 보강)
- [x] 배포용 SEO 자산 생성 (deploy/: head-snippet, JSON-LD, sitemap, robots)
- [x] 자동화 테스트 12개 (tests/test_seo_tool.py)
- [x] requirements.txt / .gitignore / LICENSE
- [x] GitHub Actions 워크플로 (주간 SEO 점검 + 테스트)
