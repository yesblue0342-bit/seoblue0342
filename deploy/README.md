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
