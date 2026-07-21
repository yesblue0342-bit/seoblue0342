#!/usr/bin/env bash
# seoblue0342 — npm_default 도커 네트워크에 컨테이너로 실행
# NPM(nginx-proxy-manager)이 컨테이너 이름 'seoblue0342:8842' 로 바로 연결 가능해짐
set -euo pipefail

NETWORK=npm_default
NAME=seoblue0342
DATA_VOLUME=seoblue0342-data
STELLA_ENV_FILE="${STELLA_ENV_FILE:-/opt/stella-ai-workspace/.env}"

DRIVE_ENV_FILE="$(mktemp)"
trap 'rm -f "$DRIVE_ENV_FILE"' EXIT
chmod 600 "$DRIVE_ENV_FILE"
BACKUP_NAME=""

cd "$(dirname "$0")/.."

# Stella와 앱은 별도 컨테이너라 환경변수가 자동 상속되지 않는다. Stella 전체 .env를
# 넘기지 않고 Drive OAuth 3개만 앱 설정 우선순위로 임시 파일에 추출한다.
APP_ENV="$PWD/.env"
echo "▶ Google Drive OAuth 설정 준비"
python3 deploy/resolve_drive_env.py \
  --primary "$APP_ENV" \
  --fallback "$STELLA_ENV_FILE" \
  --output "$DRIVE_ENV_FILE" \
  --enable-writes

# 앱 루트(.env)의 기존 설정과 최소 Drive OAuth 설정을 컨테이너에 주입한다.
ENV_ARGS=()
if [ -f "$PWD/.env" ]; then
  ENV_ARGS+=(--env-file "$PWD/.env")
  echo "▶ .env 발견 — 환경변수 주입 ($PWD/.env)"
else
  echo "⚠️ 앱 .env 없음 — 세션·SEO API 설정은 기본값으로 실행됩니다."
fi
ENV_ARGS+=(--env-file "$DRIVE_ENV_FILE")

echo "▶ 기존 systemd 서비스 중지 (8842 점유 해제)"
sudo systemctl disable --now seoblue0342 2>/dev/null || true

echo "▶ 이미지 빌드"
sudo docker build -t "$NAME" .

echo "▶ 배포 전 Google Drive token·API·전체 scope 확인"
if sudo docker run --rm "${ENV_ARGS[@]}" "$NAME" python -c \
  'from drive_service import DriveClient; DriveClient().verify_connection(require_full_access=True); print("  ✅ Google Drive 읽기/쓰기 전체 scope 확인")'; then
  :
else
  echo "  ❌ 기존 서비스는 유지합니다. Google OAuth 세트와 전체 scope를 확인하세요."
  exit 1
fi

rollback_deploy() {
  echo "▶ 실패한 새 컨테이너 정리 및 이전 버전 복구"
  sudo docker logs --tail 100 "$NAME" 2>/dev/null || true
  sudo docker rm -f "$NAME" 2>/dev/null || true
  if [ -n "$BACKUP_NAME" ] && sudo docker inspect "$BACKUP_NAME" >/dev/null 2>&1; then
    sudo docker rename "$BACKUP_NAME" "$NAME"
    sudo docker start "$NAME" >/dev/null
    echo "  ✅ 이전 컨테이너 복구 완료"
  fi
}

if sudo docker inspect "$NAME" >/dev/null 2>&1; then
  BACKUP_NAME="${NAME}-rollback-$(date +%s%N)"
  echo "▶ 기존 컨테이너 백업 ($BACKUP_NAME)"
  if ! sudo docker stop "$NAME" >/dev/null; then
    echo "  ❌ 기존 컨테이너를 안전하게 중지하지 못했습니다. 배포를 중단합니다."
    exit 1
  fi
  if ! sudo docker rename "$NAME" "$BACKUP_NAME"; then
    sudo docker start "$NAME" >/dev/null || true
    echo "  ❌ 기존 컨테이너 백업에 실패해 이전 서비스를 다시 시작했습니다."
    exit 1
  fi
fi

echo "▶ $NETWORK 네트워크에 컨테이너 실행"
if ! sudo docker run -d --name "$NAME" \
    --network "$NETWORK" \
    --restart unless-stopped \
    --volume "$DATA_VOLUME:/app/data" \
    "${ENV_ARGS[@]}" \
    "$NAME"; then
  rollback_deploy
  exit 1
fi

echo "▶ 헬스체크 (10초 대기)"
sleep 10
if sudo docker exec "$NAME" curl -fsS http://127.0.0.1:8842/healthz \
  | python3 -c 'import json,sys; h=json.load(sys.stdin); raise SystemExit(0 if h.get("ok") and h.get("drive_configured") and h.get("drive_writes_enabled") else 1)'; then
  echo "  ✅ 컨테이너 및 Google Drive 설정 정상"
else
  echo "  ❌ 컨테이너 또는 Google Drive 설정 비정상"
  rollback_deploy
  exit 1
fi

if [ -n "$BACKUP_NAME" ]; then
  sudo docker rm "$BACKUP_NAME" >/dev/null
  echo "▶ 이전 컨테이너 백업 정리 완료"
fi

echo ""
echo "🎉 완료. 이제 NPM에서 Forward 를 아래로 설정하세요:"
echo "   Forward Hostname / IP : $NAME"
echo "   Forward Port          : 8842"
