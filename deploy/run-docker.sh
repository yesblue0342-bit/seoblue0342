#!/usr/bin/env bash
# seoblue0342 — npm_default 도커 네트워크에 컨테이너로 실행
# NPM(nginx-proxy-manager)이 컨테이너 이름 'seoblue0342:8842' 로 바로 연결 가능해짐
set -euo pipefail

NETWORK=npm_default
NAME=seoblue0342
DATA_VOLUME=seoblue0342-data

cd "$(dirname "$0")/.."

echo "▶ 기존 systemd 서비스 중지 (8842 점유 해제)"
sudo systemctl disable --now seoblue0342 2>/dev/null || true

echo "▶ 이미지 빌드"
sudo docker build -t "$NAME" .

echo "▶ 기존 컨테이너 정리"
sudo docker rm -f "$NAME" 2>/dev/null || true

# 앱 루트(.env)의 환경변수(SERPER_API_KEY 등)를 컨테이너에 자동 주입.
# .env는 gitignore 대상이라 저장소엔 없고 호스트에만 존재 → 배포 때마다 키 유실 방지.
ENV_ARG=""
if [ -f "$PWD/.env" ]; then
  ENV_ARG="--env-file $PWD/.env"
  echo "▶ .env 발견 — 환경변수 주입 ($PWD/.env)"
else
  echo "⚠️ .env 없음 — 인증·Drive·SEO API 환경변수가 주입되지 않습니다."
  echo "   호스트 앱 루트($PWD)에서 '.env.example'을 참고해 .env를 작성하세요."
fi

echo "▶ $NETWORK 네트워크에 컨테이너 실행"
sudo docker run -d --name "$NAME" \
  --network "$NETWORK" \
  --restart unless-stopped \
  --volume "$DATA_VOLUME:/app/data" \
  $ENV_ARG \
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
