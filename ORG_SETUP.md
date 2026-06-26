# OCI 자동배포 — 조직(Organization) 표준화 가이드

> 목표: **모든 레포 + 앞으로 생기는 신규 레포까지** OCI 서버로 자동 배포.
> 개인 계정엔 공유 시크릿이 없으므로 무료 Organization을 만들어 시크릿 1회 등록.

## 역할 분담
- **사용자만 가능(계정/UI 권한)**: ① 조직 생성 ② 레포 이전 ③ SSH 키 시크릿 등록
- **이미 준비됨(이 레포)**: 레포 비종속 워크플로(`deploy/org-template/`), 본 체크리스트

## 체크리스트

### 1) 무료 Organization 생성  ⟶ 사용자
- https://github.com/account/organizations/new → **Free** 선택
- 조직명 예: `stella-ai` (정해지면 알려주세요)

### 2) OCI 앱 레포만 이전  ⟶ 사용자
- 대상: `seoblue0342` (+ 원하면 `stella-ai-workspace`)
- 각 레포 → Settings → 맨 아래 **Transfer ownership** → 새 조직
- ⚠️ Vercel(stella-clover)·Pages(Leehu) 레포는 연동 끊김 우려 → 이전하지 말 것

### 3) 조직 시크릿 1회 등록  ⟶ 사용자
- 조직 → Settings → **Secrets and variables → Actions → New organization secret**
- `OCI_SSH_HOST`, `OCI_SSH_USER`, `OCI_SSH_KEY` (+선택 `OCI_SSH_PORT`)
- **Repository access = All repositories** → 신규 레포 자동 상속 ✅
- ❌ `OCI_APP_DIR`은 넣지 말 것 (워크플로가 `/opt/<레포명>` 자동 결정)

### 4) 신규 레포용 워크플로 템플릿  ⟶ 사용자(1회) + 준비물 제공
조직에 **`.github` 라는 이름의 공개 레포**를 만들고 아래를 넣으면,
새 워크플로 추가 화면에서 "Deploy to OCI" 가 한 클릭으로 삽입됨:
- `.github/workflow-templates/deploy-oci.yml`        ← `deploy/org-template/deploy-oci.yml`
- `.github/workflow-templates/deploy-oci.properties.json` ← `deploy/org-template/deploy-oci.properties.json`

### 5) OCI 서버 클론 경로 정합성  ⟶ 사용자(서버)
- 워크플로는 `/opt/<레포명>` 으로 배포함 → 서버에도 같은 경로로 clone 되어 있어야 함
  - 예: `sudo git clone <repo> /opt/seoblue0342`
- 한 번만 맞춰두면 이후 push마다 자동 `git reset --hard` + 재빌드

## 결과
- 기존 OCI 레포: push 시 자동 배포
- **신규 레포**: 템플릿에서 워크플로 1클릭 추가 → 조직 시크릿 자동 상속 → 추가 설정 0
