#!/bin/bash
# Today Tactics — Rocky Linux (RHEL 계열) VPS 초기 설정 스크립트
# 사용법: bash setup.sh
set -e

APP_DIR="/opt/today_tatics"
APP_USER="tactics"
REPO="https://github.com/bbang-bbang/today_tatics.git"

echo "▶ EPEL 저장소 활성화"
dnf install -y epel-release

echo "▶ 시스템 업데이트"
dnf update -y -q

echo "▶ 패키지 설치"
dnf install -y python3 python3-pip nginx git curl

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
# Rocky에서 install-deps가 실패하면 무시 (주요 의존성은 dnf로 이미 설치됨)
sudo -u $APP_USER $APP_DIR/.venv/bin/playwright install-deps chromium || true

echo "▶ 로그 디렉토리 생성"
mkdir -p /var/log/today_tatics
chown $APP_USER:$APP_USER /var/log/today_tatics

echo "▶ 디렉토리 권한"
mkdir -p $APP_DIR/saves $APP_DIR/squads $APP_DIR/data
chown -R $APP_USER:$APP_USER $APP_DIR

echo "▶ systemd 서비스 등록"
cp /tmp/today_tatics.service /etc/systemd/system/today_tatics.service
systemctl daemon-reload
systemctl enable today_tatics
systemctl start today_tatics

echo "▶ Nginx 설정"
# Rocky는 sites-available/enabled 없이 conf.d/ 사용
cp /tmp/today_tatics.nginx /etc/nginx/conf.d/today_tatics.conf
nginx -t && systemctl enable --now nginx

echo "▶ SELinux — Nginx → Gunicorn 프록시 허용"
setsebool -P httpd_can_network_connect 1

echo "▶ 방화벽 설정 (firewalld)"
systemctl enable --now firewalld
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

echo ""
echo "✅ 설치 완료!"
echo "   앱 상태: systemctl status today_tatics"
echo "   로그:    journalctl -u today_tatics -f"
