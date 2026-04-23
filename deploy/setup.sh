#!/bin/bash
# Today Tactics — Hetzner VPS 초기 설정 스크립트
# 사용법: bash setup.sh
set -e

APP_DIR="/opt/today_tatics"
APP_USER="tactics"
REPO="https://github.com/bbang-bbang/today_tatics.git"

echo "▶ 시스템 업데이트"
apt-get update -qq && apt-get upgrade -y -qq

echo "▶ 패키지 설치"
apt-get install -y -qq python3 python3-pip python3-venv nginx git ufw curl

echo "▶ 앱 유저 생성"
id -u $APP_USER &>/dev/null || useradd -m -s /bin/bash $APP_USER

echo "▶ 앱 디렉토리 설정"
mkdir -p $APP_DIR
git clone $REPO $APP_DIR || (cd $APP_DIR && git pull)
chown -R $APP_USER:$APP_USER $APP_DIR

echo "▶ Python 가상환경 + 패키지"
sudo -u $APP_USER python3 -m venv $APP_DIR/.venv
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -q --upgrade pip
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -q flask gunicorn playwright

echo "▶ Playwright Chromium 설치"
sudo -u $APP_USER $APP_DIR/.venv/bin/playwright install chromium
sudo -u $APP_USER $APP_DIR/.venv/bin/playwright install-deps chromium

echo "▶ 디렉토리 권한"
mkdir -p $APP_DIR/saves $APP_DIR/squads $APP_DIR/data
chown -R $APP_USER:$APP_USER $APP_DIR

echo "▶ systemd 서비스 등록"
cp /tmp/today_tatics.service /etc/systemd/system/today_tatics.service
systemctl daemon-reload
systemctl enable today_tatics
systemctl start today_tatics

echo "▶ Nginx 설정"
cp /tmp/today_tatics.nginx /etc/nginx/sites-available/today_tatics
ln -sf /etc/nginx/sites-available/today_tatics /etc/nginx/sites-enabled/today_tatics
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "▶ 방화벽 설정"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo ""
echo "✅ 설치 완료!"
echo "   앱 상태: systemctl status today_tatics"
echo "   로그:    journalctl -u today_tatics -f"
