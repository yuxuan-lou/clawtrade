#!/bin/bash
set -e

load_secret_file() {
    local var_name="$1"
    local file_var_name="${var_name}_FILE"
    local file_path="${!file_var_name}"
    if [ -n "$file_path" ] && [ -f "$file_path" ]; then
        export "$var_name=$(tr -d '\r' < "$file_path")"
    fi
}

load_secret_file "IBEAM_ACCOUNT"
load_secret_file "IBEAM_PASSWORD"

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
export IBEAM_CHROME_DRIVER_PATH=/usr/local/bin/chromedriver
export IBEAM_TWO_FA_SELECT_TARGET="IB Key"
export IBEAM_ROUTE_VALIDATE="/v1/api/sso/validate"
export IBEAM_ROUTE_REAUTHENTICATE="/v1/api/iserver/reauthenticate?force=true"
export IBEAM_OAUTH_TIMEOUT=120
export IBEAM_PAGE_LOAD_TIMEOUT=120
export IBEAM_REAUTHENTICATE_WAIT=30
export IBEAM_MAX_REAUTHENTICATE_RETRIES=10

python3 -m ibeam.ibeam_starter --authenticate || {
    echo "⚠️  Authentication failed — check credentials or retry"
    echo "    You can retry later: docker compose exec ibkr-gateway python3 -m ibeam.ibeam_starter --authenticate"
}

echo ">>> Starting keepalive service..."
python3 /opt/gateway/keepalive.py &

echo ">>> Gateway ready"

wait
