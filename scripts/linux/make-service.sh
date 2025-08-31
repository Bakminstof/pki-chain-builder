#!/usr/bin/env bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

pushd "$SCRIPT_DIR/../.."

ROOT_DIR="$(pwd)"

SERVICE_NAME="crl_server"
SERVICE_DESC="CRL Web Service"
SERVICE_USER="$(whoami)"

WORK_DIR="$ROOT_DIR/src"
EXEC_CMD="""'$ROOT_DIR/env/python-3.12.10-embed-amd64-linux/bin/python3.12' 'crl_server/main.py' --host=0.0.0.0"""
# ==================
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

cat <<EOF | sudo tee $SERVICE_FILE > /dev/null
[Unit]
Description=$SERVICE_DESC
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$WORK_DIR
ExecStart=$EXEC_CMD
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

sleep 2

echo "Service $SERVICE_NAME installed and started"

sudo systemctl status --no-pager $SERVICE_NAME

popd
