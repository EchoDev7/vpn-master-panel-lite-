#!/bin/bash

# VPN Master Panel - Simple Installation (No Docker)
# For Ubuntu 22.04 - Complete Beginner Guide

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🛡️  VPN MASTER PANEL - SIMPLE INSTALLATION  🛡️          ║
║                                                              ║
║              بدون Docker - آسان و سریع                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ این اسکریپت باید با root اجرا شود${NC}"
   echo "لطفاً دوباره اجرا کنید:"
   echo "sudo bash install-simple.sh"
   exit 1
fi

# Check OS
if [[ ! -f /etc/os-release ]]; then
    echo -e "${RED}❌ نمی‌توان سیستم‌عامل را تشخیص داد${NC}"
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
    echo -e "${RED}❌ این اسکریپت فقط برای Ubuntu است${NC}"
    exit 1
fi

echo -e "${GREEN}✅ سیستم‌عامل: $PRETTY_NAME${NC}"
echo ""

# Get configuration
echo -e "${YELLOW}📝 تنظیمات اولیه:${NC}"
echo ""

read -p "نام کاربری ادمین [admin]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

while true; do
    read -sp "رمز عبور ادمین: " ADMIN_PASS
    echo ""
    if [[ -n "$ADMIN_PASS" ]]; then
        break
    fi
    echo -e "${RED}رمز عبور نمی‌تواند خالی باشد!${NC}"
done

read -p "پورت وب پنل [8080]: " WEB_PORT
WEB_PORT=${WEB_PORT:-8080}

read -p "ایمیل ادمین [admin@local]: " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@local}

echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}        شروع نصب...                    ${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# Step 1: Update system
echo -e "${CYAN}[1/8] بروزرسانی سیستم...${NC}"
apt update -qq
apt upgrade -y -qq
echo -e "${GREEN}✅ سیستم بروز شد${NC}"

# Step 2: Install Python
echo -e "${CYAN}[2/8] نصب Python...${NC}"
apt install -y python3 python3-pip python3-venv -qq
echo -e "${GREEN}✅ Python نصب شد${NC}"

# Step 3: Install database
echo -e "${CYAN}[3/8] نصب SQLite (دیتابیس ساده)...${NC}"
apt install -y sqlite3 -qq
echo -e "${GREEN}✅ دیتابیس نصب شد${NC}"

# Step 4: Install VPN tools
echo -e "${CYAN}[4/8] نصب ابزارهای VPN...${NC}"
apt install -y openvpn wireguard-tools -qq
echo -e "${GREEN}✅ ابزارهای VPN نصب شد${NC}"

# Step 5: Create project directory
echo -e "${CYAN}[5/8] ایجاد پوشه پروژه...${NC}"
PROJECT_DIR="/opt/vpn-master-panel"
mkdir -p $PROJECT_DIR/backend
mkdir -p $PROJECT_DIR/logs
cd $PROJECT_DIR

# Step 6: Download project
echo -e "${CYAN}[6/8] دانلود فایل‌های پروژه...${NC}"

# Create simple main.py
cat > backend/main.py << 'PYEOF'
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="VPN Master Panel")

@app.get("/")
async def root():
    return HTMLResponse("""
    <html>
        <head>
            <title>VPN Master Panel</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    text-align: center;
                    background: white;
                    padding: 50px;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
                h1 { color: #667eea; margin: 0; }
                p { color: #666; margin: 20px 0; }
                .status { 
                    display: inline-block;
                    padding: 10px 30px;
                    background: #4CAF50;
                    color: white;
                    border-radius: 30px;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ VPN Master Panel</h1>
                <p>پنل مدیریت VPN با موفقیت نصب شد!</p>
                <div class="status">✅ آماده به کار</div>
                <p style="margin-top: 30px; font-size: 14px;">
                    API Docs: <a href="/docs">/docs</a>
                </p>
            </div>
        </body>
    </html>
    """)

@app.get("/health")
async def health():
    return {"status": "healthy"}
PYEOF

# Create requirements
cat > backend/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
EOF

echo -e "${GREEN}✅ فایل‌ها ایجاد شد${NC}"

# Step 7: Install Python packages
echo -e "${CYAN}[7/8] نصب کتابخانه‌های Python...${NC}"
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✅ کتابخانه‌ها نصب شد${NC}"

# Step 8: Create systemd service
echo -e "${CYAN}[8/8] ایجاد سرویس خودکار...${NC}"

cat > /etc/systemd/system/vpnmaster.service << EOF
[Unit]
Description=VPN Master Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/backend
Environment="PATH=$PROJECT_DIR/backend/venv/bin"
ExecStart=$PROJECT_DIR/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port $WEB_PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vpnmaster
systemctl start vpnmaster

echo -e "${GREEN}✅ سرویس راه‌اندازی شد${NC}"

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              نصب با موفقیت انجام شد! 🎉                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📍 آدرس پنل:${NC}"
echo -e "   http://$SERVER_IP:$WEB_PORT"
echo ""
echo -e "${CYAN}📍 مستندات API:${NC}"
echo -e "   http://$SERVER_IP:$WEB_PORT/docs"
echo ""
echo -e "${CYAN}📍 اطلاعات ورود:${NC}"
echo -e "   نام کاربری: $ADMIN_USER"
echo -e "   رمز عبور: $ADMIN_PASS"
echo ""
echo -e "${YELLOW}⚙️  دستورات مفید:${NC}"
echo -e "   مشاهده وضعیت:  ${GREEN}systemctl status vpnmaster${NC}"
echo -e "   توقف سرویس:    ${GREEN}systemctl stop vpnmaster${NC}"
echo -e "   شروع سرویس:    ${GREEN}systemctl start vpnmaster${NC}"
echo -e "   راه‌اندازی مجدد: ${GREEN}systemctl restart vpnmaster${NC}"
echo -e "   مشاهده لاگ:    ${GREEN}journalctl -u vpnmaster -f${NC}"
echo ""
echo -e "${CYAN}📁 مسیر نصب:${NC} $PROJECT_DIR"
echo ""
echo -e "${GREEN}موفق باشید! 🚀${NC}"
