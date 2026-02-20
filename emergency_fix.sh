#!/bin/bash
# ════════════════════════════════════════════════════════════
#  VPN Master Panel — EMERGENCY FIX
#  Run: sudo bash emergency_fix.sh
# ════════════════════════════════════════════════════════════

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}▶ Emergency Fix Started...${NC}"

# ── Step 1: Restore backed-up Nginx config (if ssl swap left it broken) ──
BAK="/etc/nginx/sites-available/vpnmaster.bak_ssl"
CONF="/etc/nginx/sites-available/vpnmaster"

if [ -f "$BAK" ]; then
    echo -e "${YELLOW}Found backup config — restoring...${NC}"
    cp -f "$BAK" "$CONF"
    rm -f "$BAK"
    echo -e "${GREEN}✓ Config restored from backup${NC}"
fi

# ── Step 2: Write a known-good Nginx config ──────────────────────────────
echo -e "${CYAN}▶ Writing known-good Nginx config...${NC}"
cat > /etc/nginx/sites-available/vpnmaster << 'NGINXEOF'
# VPN Master Panel — Emergency restored config

server {
    listen 0.0.0.0:80;
    server_name _;
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }
    location / {
        return 200 "VPN Master Panel OK";
        add_header Content-Type text/plain;
    }
}

server {
    listen 0.0.0.0:8000;
    server_name _;

    location /api/ {
        proxy_pass         http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout  600s;
        proxy_send_timeout  600s;
        proxy_connect_timeout 30s;
        proxy_buffering    off;
        proxy_cache        off;
        chunked_transfer_encoding on;
        add_header X-Accel-Buffering no always;
    }

    location /ws/ {
        proxy_pass         http://127.0.0.1:8001/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_read_timeout 3600s;
        proxy_buffering    off;
    }

    location / {
        proxy_pass         http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header   Host       $host;
        proxy_read_timeout 600s;
        proxy_buffering    off;
    }
}

server {
    listen 0.0.0.0:3000;
    server_name _;

    root  /opt/vpn-master-panel/frontend/dist;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 1000;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass         http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_read_timeout  600s;
        proxy_buffering     off;
        proxy_cache         off;
        chunked_transfer_encoding on;
        add_header X-Accel-Buffering no always;
    }

    location /ws/ {
        proxy_pass         http://127.0.0.1:8001/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_read_timeout 3600s;
        proxy_buffering    off;
    }
}
NGINXEOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/vpnmaster /etc/nginx/sites-enabled/vpnmaster

# ── Step 3: Also remove any domain-specific broken SSL configs ───────────
for broken_conf in /etc/nginx/sites-enabled/vpn_panel_*; do
    if [ -L "$broken_conf" ]; then
        target=$(readlink -f "$broken_conf")
        # Test the target config
        if ! nginx -t -c /dev/stdin <<< "events{} http{ include $target; }" > /dev/null 2>&1; then
            echo -e "${YELLOW}Removing broken SSL config: $broken_conf${NC}"
            rm -f "$broken_conf"
        fi
    fi
done

# ── Step 4: Test and restart Nginx ────────────────────────────────────────
echo -e "${CYAN}▶ Testing Nginx config...${NC}"
if nginx -t 2>&1; then
    echo -e "${GREEN}✓ Config valid${NC}"
    systemctl restart nginx
    sleep 2
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✓ Nginx is running${NC}"
    else
        echo -e "${RED}✗ Nginx failed to start — check: journalctl -u nginx -n 20${NC}"
    fi
else
    echo -e "${RED}✗ Nginx config still invalid!${NC}"
    echo -e "${YELLOW}Trying to disable all site configs and use minimal...${NC}"
    rm -f /etc/nginx/sites-enabled/*
    cat > /etc/nginx/sites-enabled/emergency << 'ECONF'
server {
    listen 0.0.0.0:8000;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }
}
server {
    listen 0.0.0.0:3000;
    server_name _;
    root /opt/vpn-master-panel/frontend/dist;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
}
ECONF
    nginx -t && systemctl restart nginx
fi

# ── Step 5: Ensure backend is running ─────────────────────────────────────
echo -e "${CYAN}▶ Checking backend...${NC}"
if ! systemctl is-active --quiet vpnmaster-backend; then
    echo -e "${YELLOW}Backend is down — restarting...${NC}"
    systemctl restart vpnmaster-backend
    sleep 3
fi

if systemctl is-active --quiet vpnmaster-backend; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend failed — check: journalctl -u vpnmaster-backend -n 30${NC}"
fi

# ── Step 6: Final status ──────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Status Report${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
systemctl is-active --quiet nginx && echo -e "  Nginx:   ${GREEN}✓ Running${NC}" || echo -e "  Nginx:   ${RED}✗ Down${NC}"
systemctl is-active --quiet vpnmaster-backend && echo -e "  Backend: ${GREEN}✓ Running${NC}" || echo -e "  Backend: ${RED}✗ Down${NC}"
echo ""
echo -e "  Port 3000: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ 2>/dev/null || echo 'unreachable')"
echo -e "  Port 8000: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/ 2>/dev/null || echo 'unreachable')"
echo -e "  Backend:   $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/ 2>/dev/null || echo 'unreachable')"
echo ""
echo -e "${GREEN}✅ Emergency fix complete!${NC}"
echo -e "  Open panel: http://YOUR_SERVER_IP:3000"
