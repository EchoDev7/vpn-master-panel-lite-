#!/bin/bash

# Exit on error
set -e

echo "🚀 Installing VPN Master Panel Service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root"
  exit 1
fi

SERVICE_FILE="vpn-panel-backend.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_FILE"
SOURCE_PATH="/opt/vpn-master-panel/backend/service/$SERVICE_FILE"

# Copy service file
if [ -f "$SOURCE_PATH" ]; then
    echo "📄 Copying service file..."
    cp "$SOURCE_PATH" "$SERVICE_PATH"
else
    echo "❌ Service file not found at $SOURCE_PATH"
    echo "Creating it manually..."
    cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=VPN Master Panel Backend
After=network.target

[Service]
User=root
WorkingDirectory=/opt/vpn-master-panel/backend
Environment="PATH=/opt/vpn-master-panel/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/vpn-master-panel/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
fi

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable and start service
echo "✅ Enabling service..."
systemctl enable vpn-panel-backend

echo "▶️ Starting service..."
systemctl restart vpn-panel-backend

# Check status
echo "📊 Checking status..."
systemctl status vpn-panel-backend --no-pager

echo "🎉 Done! Service is running and will auto-start on boot."
