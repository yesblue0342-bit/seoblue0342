# 📈 이후 소설가 — 네이버 SEO 최적화 도구

네이버에서 "이후" 검색 시 소설가 이후의 정보가 **상위 노출**되도록 돕는 SEO 분석·모니터링 도구입니다.

---

## 🚀 빠른 시작

```bash
# 의존성 설치
pip install requests beautifulsoup4 rich lxml

# 전체 분석 실행 (순위 체크 + SEO 분석 + 리포트 생성)
python main.py

# 리포트를 특정 폴더에 저장
python main.py --output-dir ./reports
```

---

## 📋 주요 기능

| 기능 | 설명 |
|------|------|
| **네이버 순위 모니터** | "이후" 검색 시 내 페이지(네이버 프로필, 위키백과, 홈페이지) 순위 확인 |
| **SEO 분석** | 홈페이지·위키백과의 15개 SEO 항목 분석 (Title, 메타태그, OG, JSON-LD 등) |
| **개선 권고안** | 항목별 구체적인 수정 방법 제시 |
| **네이버 전략 가이드** | 동명이인 차별화, 네이버 웹마스터, 블로그 활용 등 8가지 전략 |
| **히스토리 DB** | SQLite에 순위 변동 이력 저장 |
| **HTML/MD 리포트** | 브라우저에서 볼 수 있는 시각적 리포트 파일 생성 |

---

## 🖥️ 사용법

```bash
# 전체 분석 (기본)
python main.py

# 순위 체크만
python main.py --rank-only

# SEO 분석만 (네이버 요청 없이)
python main.py --seo-only

# 순위 히스토리 조회
python main.py --history

# 리포트 파일 생성 없이 실행
python main.py --no-report

# 리포트 저장 경로 지정
python main.py --output-dir /path/to/reports
```

---

## 📁 파일 구조

```
seoblue0342/
├── main.py              # 메인 실행 파일
├── config.py            # 설정 (키워드, URL, 헤더 등)
├── rank_monitor.py      # 네이버 검색 순위 체크 + DB
├── seo_analyzer.py      # 페이지별 SEO 15항목 분석
├── report_generator.py  # HTML·마크다운 리포트 생성
├── dashboard.py         # rich CLI 대시보드
├── requirements.txt     # 의존성
├── LICENSE              # MIT
├── tests/
│   └── test_seo_tool.py # 자동화 테스트 (12개)
├── deploy/              # ★ 홈페이지에 실제 배포하는 SEO 자산
│   ├── head-snippet.html      # <head>용 메타태그+JSON-LD 일괄 블록
│   ├── structured-data.jsonld # Person/Book 스키마
│   ├── sitemap.xml            # 사이트맵
│   ├── robots.txt             # 크롤러 허용 + 사이트맵 위치
│   └── README.md              # 배포 방법 안내
├── .github/workflows/
│   └── seo-check.yml    # 주간 자동 SEO 점검 + 테스트 (GitHub Actions)
└── reports/             # 생성된 리포트 파일들 (자동 생성)
```

> 📂 **`deploy/` 폴더가 "실제 배포할 수 있는 확장자 파일"입니다.**
> `.html` / `.jsonld` / `.xml` / `.txt` — 이후.com 홈페이지에 올리면 SEO 점수가 즉시 보강됩니다.
> 배포 방법은 [`deploy/README.md`](deploy/README.md) 참고.

---

## 🔍 SEO 분석 항목 (15가지)

1. ✅ 페이지 Title 태그 (30~60자)
2. ✅ 핵심 키워드 "이후"가 제목에 포함
3. ✅ 메타 디스크립션 (120~160자)
4. ✅ 디스크립션에 키워드 포함
5. ✅ 메타 키워드
6. ✅ H1 헤딩
7. ✅ H2/H3 헤딩 구조
8. ✅ Canonical URL
9. ✅ Open Graph 제목 (og:title)
10. ✅ Open Graph 설명 (og:description)
11. ✅ Open Graph 이미지 (og:image)
12. ✅ JSON-LD 구조화 데이터 (Person 스키마)
13. ✅ HTML lang="ko" 속성
14. ✅ 모바일 Viewport 메타태그
15. ✅ 내부 링크 (3개 이상)

---

## 📊 현재 분석 결과 요약

| 페이지 | SEO 점수 | 주요 개선사항 |
|--------|---------|-------------|
| **이후.com (홈페이지)** | 47점 | 메타 디스크립션, Open Graph, JSON-LD, Canonical 추가 필요 |
| **위키백과** | 73점 | 메타 디스크립션, og:description 추가 권장 |

---

## 🚀 네이버 상위 노출 핵심 전략

1. **홈페이지에 JSON-LD Person 스키마 추가** (최우선)
   ```html
   <script type="application/ld+json">
   {
     "@context": "https://schema.org",
     "@type": "Person",
     "name": "이후",
     "alternateName": "이후 소설가",
     "jobTitle": "소설가",
     "url": "https://이후.com",
     "sameAs": ["https://ko.wikipedia.org/wiki/이후_(소설가)"]
   }
   </script>
   ```

2. **네이버 웹마스터 도구** 등록: https://searchadvisor.naver.com

3. **모든 채널에서 "이후 소설가" 수식어 일관 사용** (동명이인 차별화)

4. **네이버 블로그** 정기 포스팅 (신간, 수상 소식 등)

---

## ⚙️ 기술 스택

- Python 3.11+
- `requests` + `BeautifulSoup4`: 페이지 크롤링·파싱
- `rich`: 터미널 대시보드
- `sqlite3`: 순위 히스토리 저장
- `lxml`: HTML 파서
- `pytest`: 자동화 테스트

---

## 📝 참고사항

- 네이버 검색 순위 체크는 robots.txt를 존중하며 요청 간 딜레이를 줍니다.
- 매주 1회 실행을 권장합니다.
- 순위 체크 시 네이버의 봇 방지 정책으로 인해 결과가 제한될 수 있습니다.
  이 경우 `--seo-only` 옵션으로 SEO 분석만 실행하세요.
