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
| tests/test_seo_tool.py (12개) | ✅ 12 passed |

검증 범위: config 무결성, Accept 헤더 중복 제거, SEO 체크 항목 정의,
HTML/MD 리포트 생성, rank=None 안전 처리, 점수 색상 로직, DB 저장/조회 라운드트립,
JSON-LD 유효성, **fetch 실패 결과 렌더링 회귀 테스트**.

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
