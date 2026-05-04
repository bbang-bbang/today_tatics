#!/bin/bash
# 로컬(Windows Git Bash)에서 실행 — 서버 IP를 인자로 전달
# 사용법: bash deploy/deploy.sh 1.2.3.4
set -e

SERVER_IP=$1
APP_DIR="/opt/today_tactics"

if [ -z "$SERVER_IP" ]; then
  echo "사용법: bash deploy/deploy.sh <서버IP>"
  exit 1
fi

echo "▶ [1/5] 서비스 파일 전송"
scp deploy/today_tactics.service root@$SERVER_IP:/tmp/
scp deploy/today_tactics.nginx   root@$SERVER_IP:/tmp/
scp deploy/setup.sh             root@$SERVER_IP:/tmp/

echo "▶ [2/5] 코드 동기화 (main.py + crawlers/ + static/ + templates/)"
scp main.py root@$SERVER_IP:$APP_DIR/main.py
rsync -avz --exclude '__pycache__' crawlers/  root@$SERVER_IP:$APP_DIR/crawlers/
rsync -avz                         static/    root@$SERVER_IP:$APP_DIR/static/
rsync -avz                         templates/ root@$SERVER_IP:$APP_DIR/templates/

echo "▶ [3/5] players.db 전송 (107MB, 시간 걸릴 수 있음)"
scp players.db root@$SERVER_IP:$APP_DIR/players.db

echo "▶ [4/5] data/ 폴더 동기화"
rsync -avz --progress data/ root@$SERVER_IP:$APP_DIR/data/

echo "▶ [5/5] 서비스 재시작"
ssh root@$SERVER_IP "systemctl restart today_tactics && systemctl status today_tactics --no-pager"

echo ""
echo "✅ 배포 완료! http://$SERVER_IP 에서 확인하세요"
