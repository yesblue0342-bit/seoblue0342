#!/usr/bin/env bash
#
# seoblue0342 — OCI 서버 자동 배포 스크립트
# 실행: bash deploy/setup-oci.sh
#   - /opt/seoblue0342 에 clone/pull
#   - Python venv + 의존성 설치
#   - systemd 서비스 등록 (gunicorn, 127.0.0.1:8842)
#   - Caddy에 seo.이후.com 블록 추가 + reload (HTTPS 자동)
#   - 주간 자동 갱신 타이머 등록
#
set -euo pipefail

APP_DIR=/opt/seoblue0342
REPO=https://github.com/yesblue0342-bit/seoblue0342.git
DOMAIN=seo.xn--hu5b23z.com
PORT=8842
CADDYFILE=/etc/caddy/Caddyfile
RUN_USER="${SUDO_USER:-$USER}"

echo "▶ 1/6 코드 가져오기 ($APP_DIR)"
sudo mkdir -p "$APP_DIR"
sudo chown -R "$RUN_USER":"$RUN_USER" "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

echo "▶ 2/6 Python 가상환경 + 의존성"
python3 -m venv .venv
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -r requirements.txt
mkdir -p data

echo "▶ 3/6 systemd 서비스 등록"
# 서비스 파일의 User를 실제 실행 사용자로 치환해 설치
sed "s/^User=ubuntu/User=$RUN_USER/" deploy/seoblue0342.service \
  | sudo tee /etc/systemd/system/seoblue0342.service >/dev/null
sudo cp deploy/seoblue0342-refresh.service /etc/systemd/system/
sudo cp deploy/seoblue0342-refresh.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now seoblue0342
sudo systemctl enable --now seoblue0342-refresh.timer

echo "▶ 4/6 서비스 헬스 체크"
sleep 2
if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null; then
  echo "  ✅ 앱이 127.0.0.1:$PORT 에서 응답합니다"
else
  echo "  ⚠️ 앱 응답 없음 — 'journalctl -u seoblue0342 -n 50' 로 로그 확인"
fi

echo "▶ 5/6 Caddy에 $DOMAIN 블록 추가"
if [ -f "$CADDYFILE" ] && sudo grep -q "$DOMAIN" "$CADDYFILE"; then
  echo "  이미 $DOMAIN 블록 존재 — 건너뜀"
else
  sudo tee -a "$CADDYFILE" >/dev/null <<EOF

$DOMAIN {
    reverse_proxy 127.0.0.1:$PORT
}
EOF
  echo "  추가 완료"
fi

echo "▶ 6/6 Caddy 검증 + reload"
if sudo caddy validate --config "$CADDYFILE" --adapter caddyfile 2>/dev/null; then
  sudo systemctl reload caddy || sudo systemctl restart caddy
  echo "  ✅ Caddy reload 완료"
else
  echo "  ⚠️ Caddy 설정 검증 실패 — $CADDYFILE 수동 확인 필요"
fi

echo ""
echo "🎉 배포 완료 → https://$DOMAIN"
echo "   (HTTPS 인증서 자동 발급에 최초 수십 초 소요될 수 있습니다)"
echo "   로그: journalctl -u seoblue0342 -f"
