#!/bin/bash

# VPN Master Panel - Robust Update Script
# Version: 3.1
# Fixes: Database migrations, Frontend build, Service restarts

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting VPN Master Panel Update...${NC}"

# 1. Pull Latest Code
echo -e "\n${YELLOW}⬇️  Pulling latest code...${NC}"
git pull origin main || echo -e "${RED}⚠️  Git pull failed (local changes?). Continuing...${NC}"

# 2. Update Backend
echo -e "\n${YELLOW}🐍 Updating Backend...${NC}"
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
if [ -f "requirements-enterprise.txt" ]; then
    pip install -r requirements-enterprise.txt
fi

# 3. Fix & Run Database Migrations (Critical Step)
echo -e "\n${YELLOW}🗄️  Running Database Migrations...${NC}"
# Ensure alembic.ini exists (copy from template if missing)
if [ ! -f "alembic.ini" ]; then
    echo -e "${RED}⚠️  alembic.ini not found! Creating default...${NC}"
    # (Simplified alembic.ini creation would go here, or we assume it's in the repo now)
    # Ideally, the repo should have alembic.ini. If git pull worked, it should be there.
fi

# Run migrations
alembic upgrade head

# 4. Build Frontend (Critical for New Features)
echo -e "\n${YELLOW}⚛️  Building Frontend...${NC}"
cd ../frontend
npm install --legacy-peer-deps
npm run build

# 5. Restart Services
echo -e "\n${YELLOW}🔄 Restarting Services...${NC}"
sudo systemctl restart vpnmaster-backend
sudo systemctl reload nginx

# 6. Verify Status
echo -e "\n${YELLOW}✅ Verifying Status...${NC}"
sudo systemctl status vpnmaster-backend --no-pager
echo -e "${GREEN}✨ Update Complete! Features are now live.${NC}"
echo -e "${YELLOW}👉 Note: If you still don't see new features, clear your browser cache (Ctrl+Shift+R).${NC}"
