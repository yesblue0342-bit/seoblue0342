#!/usr/bin/env bash
# seoblue0342 — 매일 자동 SEO 갱신 타이머 설치 (도커 컨테이너 방식)
# 전제: seoblue0342 컨테이너가 npm_default 네트워크에 떠 있을 것
set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ refresh 서비스/타이머 설치"
sudo cp deploy/seoblue0342-refresh.service /etc/systemd/system/
sudo cp deploy/seoblue0342-refresh.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now seoblue0342-refresh.timer

echo "▶ 등록된 타이머 확인"
systemctl list-timers seoblue0342-refresh.timer --no-pager || true

echo ""
echo "✅ 매일 새벽 4시(KST) 자동 분석 등록 완료"
echo "   지금 즉시 1회 실행: sudo systemctl start seoblue0342-refresh.service"
echo ""
echo "── 빈도 바꾸려면 ───────────────────────────────"
echo "  하루 3회로: sudo systemctl edit seoblue0342-refresh.timer 후 아래로 교체"
echo "    [Timer]"
echo "    OnCalendar="
echo "    OnCalendar=*-*-* 00,08,16:00:00 UTC   # 09시/17시/익일01시 KST"
echo "  변경 후: sudo systemctl daemon-reload && sudo systemctl restart seoblue0342-refresh.timer"
