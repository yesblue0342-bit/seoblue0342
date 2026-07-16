# TEST_RESULTS — 유튜브 SERP 판정 확대 + run-docker.sh 키 자동 전달

## Baseline (main @ 25b1822)
```
python -m pytest tests/ -x -q  →  32 passed
```

## GATE 1 — (A) 유튜브 needle
- 전체 pytest: **32 passed** (신규 실패 0).
- `test_serp_youtube_watch_link_counts_as_exposed`: Serper links가 영상 링크
  (`youtube.com/watch?v=1qUVtfqvAwE`, `...=xc2ivmdltmE`)만 있어도 유튜브=노출(True).
- 회귀 없음: 같은 케이스에서 위키백과·교보문고는 미노출(False) 유지.

## GATE 2 — (B) run-docker.sh
- (a) `bash -n deploy/run-docker.sh` → **통과**.
- (b) 분기 로직 검증(실제 docker 실행 없이 시뮬레이션):
  - `.env` 있음 → `ENV_ARG="--env-file <앱루트>/.env"` 설정됨.
  - `.env` 없음 → `ENV_ARG=""` + 경고 출력 후 정상 진행.
- (c) `.gitignore` 2행에 `.env` 유지 확인. `git status`에 `.env` 미추적, 저장소에 `.env` 파일 없음.

## FINAL GATE
- pytest: **32 passed** (신규 실패 0)
- `bash -n deploy/run-docker.sh` 통과
- 유튜브 외 SERP 타깃·owned/profile 로직 무변경
- 시크릿: `git diff --cached`에 실제 키(40자 hex 등) 패턴 0건, `.env` 미커밋
- 문서: deploy/README.md에 Docker `.env` 자동 주입 안내 추가

## 한계
- 실제 `docker run --env-file` 동작은 이 환경에 docker/키가 없어 미실행 — 분기 로직 리뷰 +
  bash 문법 검사로 검증. 서버에서 `.env` 생성 후 첫 배포에서 실주입 확인 필요.
