#!/usr/bin/env bash
# seoblue0342 — npm_default 도커 네트워크에 컨테이너로 실행
# NPM(nginx-proxy-manager)이 컨테이너 이름 'seoblue0342:8842' 로 바로 연결 가능해짐
set -euo pipefail

NETWORK=npm_default
NAME=seoblue0342

cd "$(dirname "$0")/.."

echo "▶ 기존 systemd 서비스 중지 (8842 점유 해제)"
sudo systemctl disable --now seoblue0342 2>/dev/null || true

echo "▶ 이미지 빌드"
sudo docker build -t "$NAME" .

echo "▶ 기존 컨테이너 정리"
sudo docker rm -f "$NAME" 2>/dev/null || true

echo "▶ $NETWORK 네트워크에 컨테이너 실행"
sudo docker run -d --name "$NAME" \
  --network "$NETWORK" \
  --restart unless-stopped \
  "$NAME"

echo "▶ 헬스체크 (10초 대기)"
sleep 10
if sudo docker exec "$NAME" curl -fsS http://127.0.0.1:8842/healthz >/dev/null; then
  echo "  ✅ 컨테이너 내부 정상"
else
  echo "  ⚠️ 로그 확인: sudo docker logs $NAME"
fi

echo ""
echo "🎉 완료. 이제 NPM에서 Forward 를 아래로 설정하세요:"
echo "   Forward Hostname / IP : $NAME"
echo "   Forward Port          : 8842"
