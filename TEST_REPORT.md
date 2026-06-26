# TEST REPORT

생성: 2026-06-25 / 환경: Python 3.12

## 1. 정적 검증
| 항목 | 결과 |
|------|------|
| py_compile (6개 .py + 테스트) | ✅ 통과 |
| 전체 모듈 import (report_generator 부재 해결) | ✅ 통과 |

## 2. 단위/통합 테스트 (pytest)
| 항목 | 결과 |
|------|------|
| tests/test_seo_tool.py (17개) | ✅ 17 passed |

검증 범위: config 무결성, Accept 헤더 중복 제거, SEO 체크 항목 정의,
HTML/MD 리포트 생성, rank=None 안전 처리, 점수 색상 로직, DB 저장/조회 라운드트립,
JSON-LD 유효성, **fetch 실패 결과 렌더링 회귀 테스트**.

## 5. 정보 소스 확장 + Daum + OCI 배포 (260626) — 신규 4건
| 항목 | 결과 |
|------|------|
| 나무위키·다음·교보문고·구글·유튜브 URL 정의(config) | ✅ test_config_extra_sources_present |
| ANALYSIS_TARGETS 7개 소스 모두 포함 | ✅ test_analysis_targets_cover_all_sources |
| run_full_analysis 가 타겟 순회(네트워크 모킹, 다음 포함) | ✅ test_run_full_analysis_uses_targets |
| 리포트 상단 소스 메뉴(nav)+카드 앵커 렌더 | ✅ test_html_report_has_source_menu |
| deploy-oci.yml YAML 유효성 | ✅ yaml.safe_load 통과 |

> 실행 환경: Python 3.12 venv, `pytest -q` → **17 passed in 1.19s**.
> 분석 대상 7개: 홈페이지·위키백과·나무위키·다음·구글·교보문고·유튜브.
> run_full_analysis 는 ANALYSIS_TARGETS 단일출처를 순회하므로 카드·상단 메뉴·일일 배치잡에 동시 반영.
> OCI 자동배포: deploy-oci.yml (push→SSH 재빌드→/refresh). 시크릿 미설정 시 graceful skip.

## 3. 산출물 유효성
| 항목 | 결과 |
|------|------|
| deploy/structured-data.jsonld (json.load) | ✅ 유효 |
| deploy/head-snippet.html 인라인 JSON-LD | ✅ 유효 |
| deploy/sitemap.xml (XML 파싱) | ✅ 유효 |

## 4. 실행 테스트
| 항목 | 결과 |
|------|------|
| main.py --help | ✅ 정상 |
| main.py --seo-only --no-report (네트워크 차단 환경) | ✅ 크래시 없이 완주 (이전 KeyError 해결) |

> 참고: 실제 네이버/홈페이지 분석은 외부 네트워크가 열린 환경(로컬 PC, GitHub Actions)에서 수행됩니다.
> 컨테이너는 외부 도메인 접근이 차단돼 있어 fetch 단계는 graceful 실패로 처리됩니다.
