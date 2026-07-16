# WORK_REPORT — 유튜브 SERP 판정 확대 + run-docker.sh 키 자동 전달

## 결론 요약
- (A) 유튜브 노출 판정: needle에 `youtube.com/watch`·`youtube.com`을 추가해 영상 링크로만
  노출돼도 "유튜브 노출됨"으로 인정 (이전 커밋 25b1822에서 반영, 이번 미션에서 재확인).
- (B) 배포 시 키 유실 근본 원인 해결: `deploy/run-docker.sh`가 앱 루트의 `.env`를
  `--env-file`로 컨테이너에 자동 주입하도록 수정. main push → Actions 배포로 컨테이너가
  재생성돼도 SERPER_API_KEY가 유지된다.
- **사용자 조치 필요:** 호스트 앱 루트(`/opt/seoblue0342`)에 `.env` 파일을 만들고
  `SERPER_API_KEY=발급키` 한 줄을 넣어야 한다(이 파일은 gitignore, 저장소에 없음). 이후 배포는 자동.
- 유튜브 외 SERP 타깃·owned/profile 로직 무변경. 저장소에 실제 키 문자열 0건.

## Phase 0 — 정찰
- 최신 커밋: `25b1822`(유튜브 needle 확대 완료). baseline pytest: **32 passed**.
- (A) 유튜브 항목 현재값(이미 확대됨):
  ```python
  ("유튜브 채널", ["UCQdIJKAOKVI8pKIsvcFBEKA", "youtube.com/@",
               "youtube.com/watch", "youtube.com"], "...")
  ```
- (B) `deploy/run-docker.sh` 수정 전 `docker run` 블록: `-e`/`--env-file` 없이
  `sudo docker run -d --name "$NAME" --network "$NETWORK" --restart unless-stopped "$NAME"`.
  → 컨테이너 재생성 시 SERPER_API_KEY 미주입.
- `.gitignore` 2행에 `.env` 등재됨. 저장소에 `.env` 파일 없음(미추적).

## Phase 1 — (A) 유튜브 needle (기반영 확인)
- needle 4종(`채널ID`, `@handle`, `watch`, `youtube.com`). 테스트
  `test_serp_youtube_watch_link_counts_as_exposed`: watch 링크만으로 유튜브=노출,
  동시에 위키·교보는 미노출(회귀 없음).

## Phase 2 — (B) run-docker.sh 키 자동 전달
- `cd "$(dirname "$0")/.."` 뒤라 `$PWD`=앱 루트. `.env` 있으면 `ENV_ARG="--env-file $PWD/.env"`,
  없으면 경고 출력 후 계속 진행(배포 실패시키지 않음). `docker run`에 `$ENV_ARG` 삽입.
- `deploy/README.md`: Docker 배포 시 호스트 `.env`에 키를 넣으면 배포 때마다 자동 주입된다는 안내 추가.
- `.env` 파일은 생성하지 않음(호스트에서 사용자가 생성).

## GATE 검증 → TEST_RESULTS.md
