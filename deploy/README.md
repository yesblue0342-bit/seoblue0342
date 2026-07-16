# 🚀 배포용 SEO 자산 (deploy/)

이 폴더의 파일들은 **이후.com (xn--hu5b23z.com) 홈페이지에 실제로 올려서 배포**하는 SEO 자산입니다.
SEO 분석 도구가 지적한 홈페이지 누락 항목(메타 디스크립션·Open Graph·JSON-LD·Canonical)을 한 번에 보강합니다.

> 홈페이지는 GitHub Pages(`yesblue0342-bit/Leehu`)로 운영 중이므로,
> 해당 저장소에 아래 파일을 추가/반영하면 됩니다.

---

## 파일별 배포 방법

### 1. `head-snippet.html` → 홈페이지 `index.html`의 `<head>` 안에 붙여넣기
가장 중요합니다. 홈페이지 `index.html`을 열고 `<head>...</head>` 사이에 내용을 붙여넣으세요.
- 이미 `<title>` / `<meta viewport>`가 있으면 중복 라인은 지웁니다.
- `naver-site-verification`, `google-site-verification` 값은 각각
  네이버 서치어드바이저 / 구글 서치콘솔에서 발급받은 코드를 넣습니다.
- `og:image` 경로(`og-image.jpg`)는 1200×630 대표 이미지를 올린 뒤 실제 경로로 바꿉니다.

### 2. `sitemap.xml` → 홈페이지 **루트**에 업로드
`https://xn--hu5b23z.com/sitemap.xml` 로 접근 가능해야 합니다.
업로드 후 네이버 서치어드바이저 → 요청 → 사이트맵 제출에 등록합니다.

### 3. `robots.txt` → 홈페이지 **루트**에 업로드
`https://xn--hu5b23z.com/robots.txt` 로 접근 가능해야 합니다.
네이버 크롤러(Yeti)·구글봇 허용 + 사이트맵 위치가 명시돼 있습니다.

### 4. `structured-data.jsonld` (참고용 / 분리 관리용)
`head-snippet.html` 안에 이미 JSON-LD가 인라인으로 포함돼 있으므로
보통은 별도 업로드가 필요 없습니다. 구조화 데이터를 따로 관리하고 싶을 때 참고하세요.

---

## 구글 SERP 노출 체크 — Custom Search API 키 설정

대시보드의 "구글 검색" 카드는 스크래핑 대신 **Google Custom Search JSON API**를 사용합니다.
키가 없으면 카드가 "측정 불가"로 표시됩니다 (무료 쿼터: 일 100쿼리 — 하루 1회 분석이면 충분).

1. [Google Cloud Console](https://console.cloud.google.com/apis/library/customsearch.googleapis.com)에서 **Custom Search API 활성화** 후 API 키 발급 → `GOOGLE_CSE_API_KEY`
2. [programmablesearchengine.google.com](https://programmablesearchengine.google.com)에서 검색엔진 생성 (**"전체 웹 검색" ON**) 후 검색엔진 ID(cx) 복사 → `GOOGLE_CSE_CX`
3. 서버에서 `/etc/systemd/system/seoblue0342.service`의 `Environment=GOOGLE_CSE_...` 주석을 실제 값으로 해제하고
   `sudo systemctl daemon-reload && sudo systemctl restart seoblue0342`

---

## 배포 후 체크리스트

- [ ] 홈페이지 `<head>`에 메타태그/JSON-LD 반영
- [ ] `sitemap.xml`, `robots.txt` 루트 접근 확인
- [ ] [구글 리치 결과 테스트](https://search.google.com/test/rich-results)로 JSON-LD 검증
- [ ] 네이버 서치어드바이저에 사이트 등록 + 사이트맵/RSS 제출
- [ ] 구글 서치콘솔에 사이트 등록 + 사이트맵 제출
- [ ] 1~2주 후 `python main.py`로 순위/점수 재측정

---

## ⚠️ 내용 점검 권장

`structured-data.jsonld` / `head-snippet.html`의 인물 정보(대표작, 출생연도, 직함)는
공개 자료 기준으로 채워둔 초안입니다. 실제 프로필과 다르면 직접 수정하세요.
특히 대표작 목록(《연》·《데자뷔》·《소나기》)과 `sameAs` 링크는 최신 상태로 갱신하는 것이 좋습니다.

---

# 🖥️ OCI 서버에서 웹으로 띄우기 (seo.이후.com)

`seoblue0342`를 OCI 서버(161.33.4.91, Osaka)에서 직접 실행해 **https://seo.이후.com** 으로
서비스합니다. Vercel이 아니라 OCI의 Caddy reverse_proxy 뒤에 띄우는 구성입니다
(chat.이후.com과 동일한 방식).

## 구성 요소
- `webapp.py` — Flask 웹 진입점 (대시보드 + 🔄 다시 분석 버튼, iframe으로 리포트 표시)
- `seoblue0342.service` — gunicorn을 127.0.0.1:8842에 띄우는 systemd 서비스
- `seo.이후.com.Caddyfile` — Caddy 블록 (HTTPS 자동 발급)
- `seoblue0342-refresh.{service,timer}` — 매주 월요일 자동 재분석
- `setup-oci.sh` — 위 전부를 자동 설치하는 원클릭 스크립트

## 사전 조건 (이미 충족됨)
- DNS: `seo.이후.com` → `stella.이후.com` → 161.33.4.91 (OCI) ✅ 전파 완료
- OCI에 Caddy(`/etc/caddy/Caddyfile`)와 Python3가 설치되어 있을 것

## 배포 (OCI 서버에서 한 줄)
```bash
# 방법 A — 스크립트가 repo를 clone부터 알아서 진행
curl -fsSL https://raw.githubusercontent.com/yesblue0342-bit/seoblue0342/main/deploy/setup-oci.sh | bash

# 방법 B — 직접 clone 후 실행
git clone https://github.com/yesblue0342-bit/seoblue0342.git /opt/seoblue0342
cd /opt/seoblue0342 && bash deploy/setup-oci.sh
```

스크립트가 하는 일: `/opt/seoblue0342`에 clone → venv + 의존성 설치 →
gunicorn systemd 서비스 등록 → Caddy에 `seo.이후.com` 블록 추가 + reload →
주간 자동 갱신 타이머 등록.

## 확인
- 브라우저: **https://seo.이후.com** (최초 HTTPS 인증서 발급에 수십 초)
- 로그: `journalctl -u seoblue0342 -f`
- 상태: `systemctl status seoblue0342`

## 사용자/포트 변경
서비스 실행 사용자는 스크립트가 현재 사용자로 자동 치환합니다. 포트(기본 8842)를 바꾸려면
`seoblue0342.service`의 `-b 127.0.0.1:8842`와 `seo.이후.com.Caddyfile`의 포트를 함께 수정하세요.
