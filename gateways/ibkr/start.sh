#!/bin/bash
set -e

echo ">>> Starting virtual display..."
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99
sleep 2

echo ">>> Starting IBKR Client Portal Gateway..."
cd /opt/gateway/clientportal
bash bin/run.sh root/conf.yaml &
sleep 30

echo ">>> Starting IBeam authentication..."
echo "    Please confirm the push notification on your IBKR Key mobile app (within 2 minutes)!"

export IBEAM_GATEWAY_DIR=/opt/gateway/clientportal
export IBEAM_CHROME_DRIVER_PATH=/usr/bin/chromedriver
export IBEAM_TWO_FA_SELECT_TARGET="IB Key"

python3 -m ibeam --authenticate || {
    echo "⚠️  Authentication failed — check credentials or retry"
    echo "    You can retry later: docker compose exec ibkr-gateway python3 -m ibeam --authenticate"
}

echo ">>> Starting keepalive service..."
python3 /opt/gateway/keepalive.py &

echo ">>> Gateway ready"

wait
