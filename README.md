# 이후 도구 — SEO · G-Drive · Obsidian Download

`seo.이후.com`에서 SEO 분석과 인증 기반 파일·대화 변환 도구를 함께 제공합니다.

- `/` — 기존 네이버 SEO 분석 대시보드
- `/g-drive` — Google Drive 파일 탐색·검색·다운로드, 권한 확인 후 선택적 쓰기
- `/obsidian-download` — 공개 ChatGPT/Claude 공유 링크를 Obsidian용 Markdown으로 변환

---

## 🚀 빠른 시작

```bash
# 의존성 설치
pip install requests beautifulsoup4 rich lxml

# 웹앱 환경변수 준비
cp .env.example .env
# .env에 SEO_SESSION_SECRET, SEO_INITIAL_PASSWORD 및 필요한 Google OAuth 값을 입력

# Windows PowerShell에서는: Copy-Item .env.example .env

# 전체 분석 실행 (순위 체크 + SEO 분석 + 리포트 생성)
python main.py

# 리포트를 특정 폴더에 저장
python main.py --output-dir ./reports

# 웹앱 실행 (로컬 HTTP에서는 .env의 SEO_COOKIE_SECURE=0)
python webapp.py
```

## 계정 및 보안

최초 실행 시 `SEO_INITIAL_PASSWORD`가 설정되어 있으면 `admin`, `yesblue0342` 두 계정을 SQLite에 scrypt 해시로 생성합니다. 두 계정은 최초 로그인 직후 비밀번호를 변경하기 전까지 G-Drive와 Obsidian Download 페이지 및 API를 사용할 수 없습니다. 변경을 마치면 운영 `.env`에서 `SEO_INITIAL_PASSWORD`를 제거합니다.

- 운영 세션 쿠키: `HttpOnly`, `Secure`, `SameSite=Lax`, 8시간 만료
- 로그인: IP+아이디 기준 15분 구간에서 5회 실패 시 일시 잠금
- 상태 변경 API: 세션 인증과 CSRF 토큰을 모두 검증
- 계정/로그인 데이터: Docker 명명 볼륨 `seoblue0342-data`의 `/app/data/auth.db`
- 비밀값과 OAuth 토큰은 서버 환경변수에만 저장되며 HTML/JavaScript로 전달하지 않음

## G-Drive 설정

Stella 앱과 같은 환경변수 이름을 사용합니다.

```dotenv
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
SEO_DRIVE_WRITES_ENABLED=0
```

OCI 자동 배포에서는 앱 `.env`에 세 값이 없을 때 `/opt/stella-ai-workspace/.env`에서
Google Drive OAuth 자격증명 세 개만 추출해 임시 파일로 주입합니다. Stella의
`GOOGLE_OAUTH_*`, `GOOGLE_DRIVE_*`, `DRIVE_REFRESH_TOKEN` 별칭도 인식하며, OpenAI·DB 등
Stella의 다른 비밀값은 G-Drive 컨테이너에 전달하지 않습니다. 앱 `.env` 값이 있으면 항상
그 값을 우선합니다. Stella 경로가 다르면 배포 시 `STELLA_ENV_FILE`로 지정할 수 있습니다.
OCI 배포는 `SEO_DRIVE_WRITES_ENABLED=1`을 적용하고 실제 토큰 교환·Drive API 접근·
`https://www.googleapis.com/auth/drive` 전체 scope까지 확인해야 성공 처리됩니다.

목록, 폴더 이동, 상위 경로, 파일명 검색, 메타데이터 표시와 다운로드는 Drive API 연결 후 사용할 수 있습니다. Google Docs/Sheets/Slides는 각각 DOCX/XLSX/PPTX로 export합니다. 업로드·새 폴더·이름 변경·이동·휴지통 기능은 실제 refresh token의 OAuth scope가 쓰기를 허용하는지 확인한 뒤에만 `SEO_DRIVE_WRITES_ENABLED=1`로 활성화합니다. 쓰기 권한이 없거나 API가 403을 반환하면 앱은 읽기 전용으로 유지하고 권한 안내를 표시합니다. 웹 업로드 상한은 25MB입니다.

## Obsidian Download 저장 방식

지원 URL은 `https://chatgpt.com/share/<id>`와 `https://claude.ai/share/<id>` 형식의 접근 가능한 공유 스냅샷입니다. 비공개, 조직 전용, 로그인 필요, 만료·해제 링크는 우회하지 않고 오류로 안내합니다. 변환 결과에는 제목, 원본 URL, provider, 다운로드 시각을 YAML frontmatter로 기록하며 사용자/AI 역할, 코드 블록, 표, 목록, 링크를 가능한 범위에서 보존합니다.

브라우저는 `C:\obsidian\download`를 임의로 선택하거나 서버가 Windows 경로에 직접 쓸 수 없습니다. Chromium 계열에서는 사용자가 최초 1회 폴더를 선택하면 File System Access API의 directory handle을 브라우저 IndexedDB에 저장하고 다음 방문에 권한을 재확인합니다. 같은 파일명이 있으면 `(1)`, `(2)`를 붙여 덮어쓰지 않습니다. API 미지원 또는 권한 미부여 시 일반 브라우저 다운로드로 폴백하므로 브라우저의 기본 다운로드 폴더를 `C:\obsidian\download`로 설정하세요.

입력 링크와 변환된 대화는 서버 DB 또는 파일에 저장하지 않으며 일반 로그에도 기록하지 않습니다.

---

## 📋 주요 기능

| 기능 | 설명 |
|------|------|
| **네이버 노출 모니터** | 네이버 **공식 오픈API(webkr)**로 '소설가 이후' 검색 시 내 페이지(홈페이지·위키백과·나무위키·교보문고·유튜브)의 **노출 여부** 확인. 스크래핑 봇 차단 문제를 없앴고, 오픈API 순서는 통합검색 순위와 달라 '몇 위'가 아닌 노출 O/X만 표시(거짓 순위 방지). `NAVER_CLIENT_ID`·`NAVER_CLIENT_SECRET` 환경변수 필요, 미설정 시 '측정 불가' 표시 — 발급 절차는 `deploy/README.md` 참고 |
| **SEO 분석** | 페이지 유형별 분석 — 홈페이지(직접 관리)는 15개 온페이지 항목, 외부 프로필(위키·교보문고·유튜브)은 콘텐츠·노출 중심, 검색결과(구글·다음)는 '이후 관련 페이지 노출 여부' 평가. 구글은 스크래핑 봇 차단으로 인한 거짓 음성을 피하기 위해 **[Serper.dev](https://serper.dev) API** 사용 (`SERPER_API_KEY` 환경변수 필요, 미설정 시 0점 대신 '측정 불가' 표시 — 발급 절차는 `deploy/README.md` 참고)[^serp] |
| **개선 권고안** | 유형별로 '실제 실행 가능한' 수정 방법만 제시 (외부 페이지에 메타태그 수정 권고 같은 노이즈 제거) |
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
├── main.py              # 메인 실행 파일 (CLI)
├── webapp.py            # ★ 웹 진입점 (Flask) — OCI에서 seo.이후.com 서비스용
├── auth.py              # 계정 seed, 로그인 제한, 세션, CSRF, 비밀번호 변경
├── drive_service.py     # 서버 전용 Google Drive REST 클라이언트
├── conversation_parser.py # 공개 공유 링크 검증·가져오기·Markdown 변환
├── templates/           # 로그인, G-Drive, Obsidian Download 화면
├── static/              # 공통 반응형 UI 및 브라우저 저장 로직
├── config.py            # 설정 (키워드, URL, 헤더 등)
├── rank_monitor.py      # 네이버 검색 순위 체크 + DB
├── seo_analyzer.py      # 페이지별 SEO 15항목 분석
├── report_generator.py  # HTML·마크다운 리포트 생성
├── dashboard.py         # rich CLI 대시보드
├── requirements.txt     # 의존성
├── LICENSE              # MIT
├── tests/
│   └── test_seo_tool.py # 자동화 테스트 (12개)
├── deploy/              # ★ 배포 자산
│   ├── head-snippet.html      # 홈페이지 <head>용 메타태그+JSON-LD
│   ├── structured-data.jsonld # Person/Book 스키마
│   ├── sitemap.xml            # 사이트맵
│   ├── robots.txt             # 크롤러 허용
│   ├── setup-oci.sh           # OCI 서버 원클릭 배포 스크립트
│   ├── seoblue0342.service    # systemd 서비스 (gunicorn)
│   ├── seo.이후.com.Caddyfile # Caddy reverse_proxy 블록
│   ├── seoblue0342-refresh.*  # 주간 자동 갱신 타이머
│   └── README.md              # 배포 방법 (홈페이지 SEO + OCI 웹)
├── .github/workflows/
│   └── seo-check.yml    # 주간 자동 SEO 점검 + 테스트 (GitHub Actions)
└── reports/             # 생성된 리포트 파일들 (자동 생성)
```

> 🖥️ **OCI 서버에서 웹으로 띄우려면** (seo.이후.com): `deploy/setup-oci.sh` 한 줄이면
> clone → venv → systemd(gunicorn) → Caddy(HTTPS 자동)까지 끝납니다.
> 자세한 내용은 [`deploy/README.md`](deploy/README.md)의 "OCI 서버에서 웹으로 띄우기" 참고.

> 📂 **홈페이지 SEO 보강용 자산**(`.html`/`.jsonld`/`.xml`/`.txt`)도 `deploy/`에 있습니다.

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

[^serp]: Google Custom Search JSON API는 2025년부터 신규 프로젝트에 접근이 닫혀(호출 시 403)
    사용할 수 없어, 종료 리스크가 없고 무료 크레딧이 넉넉한 Serper.dev로 전환했습니다.
