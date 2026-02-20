#!/bin/bash
# ════════════════════════════════════════════════════════════════════
#  VPN Master Panel — Full Diagnostic Script
#  Run on the server as root:  sudo bash diagnose.sh
#  Paste the output to diagnose SSL / backend / Nginx issues.
# ════════════════════════════════════════════════════════════════════

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BLUE='\033[0;34m'; NC='\033[0m'; BOLD='\033[1m'

sep() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
hdr() { sep; echo -e "${BOLD}${BLUE}▶ $1${NC}"; sep; }
ok()  { echo -e "  ${GREEN}✓ $1${NC}"; }
err() { echo -e "  ${RED}✗ $1${NC}"; }
warn(){ echo -e "  ${YELLOW}⚠ $1${NC}"; }
info(){ echo -e "  ${CYAN}ℹ $1${NC}"; }

echo ""
echo -e "${BOLD}${CYAN}  VPN Master Panel — Diagnostic Report${NC}"
echo -e "  $(date)"
echo ""

# ── 1. Service Status ────────────────────────────────────────────────
hdr "1. Service Status"

check_service() {
    local name="$1"
    if systemctl is-active --quiet "$name" 2>/dev/null; then
        ok "$name is RUNNING"
    else
        err "$name is NOT running"
        echo "     → Try: systemctl start $name && journalctl -u $name -n 30 --no-pager"
    fi
}

check_service vpnmaster-backend
check_service nginx
check_service openvpn 2>/dev/null || check_service "openvpn@server" 2>/dev/null || info "OpenVPN not installed/configured yet"
check_service wg-quick@wg0 2>/dev/null || info "WireGuard not active"

# ── 2. Port Checks ───────────────────────────────────────────────────
hdr "2. Listening Ports"

check_port() {
    local port="$1" label="$2"
    if ss -tlnp 2>/dev/null | grep -q ":${port}\b" || \
       netstat -tlnp 2>/dev/null | grep -q ":${port}\b"; then
        ok "Port $port ($label) is LISTENING"
        ss -tlnp 2>/dev/null | grep ":${port}\b" | awk '{print "     " $0}' | head -3
    else
        err "Port $port ($label) is NOT listening"
    fi
}

check_port 8001 "FastAPI backend (internal)"
check_port 8000 "Nginx API gateway (public)"
check_port 3000 "Nginx frontend (public)"
check_port 80   "HTTP / ACME challenge"
check_port 443  "HTTPS (after SSL)"

# ── 3. Backend Connectivity Test ────────────────────────────────────
hdr "3. Backend API Connectivity (curl tests)"

info "Testing FastAPI health endpoint directly (port 8001)..."
echo ""
RESP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8001/api/v1/health 2>/dev/null || echo "000")
if [ "$RESP" = "200" ] || [ "$RESP" = "404" ] || [ "$RESP" = "422" ]; then
    ok "FastAPI backend is responding on port 8001 (HTTP $RESP)"
elif [ "$RESP" = "000" ]; then
    err "FastAPI backend NOT responding on port 8001 (connection refused)"
    echo "     → Check: journalctl -u vpnmaster-backend -n 50 --no-pager"
else
    warn "FastAPI returned HTTP $RESP on port 8001"
fi

echo ""
info "Testing Nginx API gateway (port 8000)..."
RESP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8000/api/v1/health 2>/dev/null || echo "000")
if [ "$RESP" = "200" ] || [ "$RESP" = "404" ] || [ "$RESP" = "422" ] || [ "$RESP" = "401" ]; then
    ok "Nginx API gateway responding on port 8000 (HTTP $RESP)"
elif [ "$RESP" = "000" ]; then
    err "Nginx NOT responding on port 8000 (connection refused or Nginx down)"
else
    warn "Nginx API gateway returned HTTP $RESP"
fi

echo ""
info "Testing Nginx frontend (port 3000)..."
RESP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:3000/ 2>/dev/null || echo "000")
if [ "$RESP" = "200" ]; then
    ok "Frontend served correctly on port 3000"
elif [ "$RESP" = "000" ]; then
    err "Frontend NOT accessible on port 3000"
else
    warn "Frontend returned HTTP $RESP"
fi

# ── 4. SSL Endpoint Streaming Test ──────────────────────────────────
hdr "4. SSL Streaming Endpoint Test"

echo ""
warn "NOTE: This test requires a valid JWT token."
echo "  To get your token:"
echo ""
echo "    TOKEN=\$(curl -s -X POST http://127.0.0.1:8001/api/v1/auth/login \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -d '{\"username\":\"admin\",\"password\":\"YOUR_PASS\"}' | python3 -c \"import sys,json; print(json.load(sys.stdin)['access_token'])\" 2>/dev/null)"
echo ""
echo "  Then test SSL streaming (replace DOMAIN/EMAIL):"
echo ""
echo "    curl -v --no-buffer -X POST http://127.0.0.1:8001/api/v1/settings/ssl/request \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -H \"Authorization: Bearer \$TOKEN\" \\"
echo "      -d '{\"domain\":\"panel.yourdomain.com\",\"email\":\"your@email.com\"}'"
echo ""
echo "  Via Nginx gateway (port 8000 — what the browser uses):"
echo ""
echo "    curl -v --no-buffer -X POST http://127.0.0.1:8000/api/v1/settings/ssl/request \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -H \"Authorization: Bearer \$TOKEN\" \\"
echo "      -d '{\"domain\":\"panel.yourdomain.com\",\"email\":\"your@email.com\"}'"
echo ""

# ── 5. Nginx Config Test ─────────────────────────────────────────────
hdr "5. Nginx Configuration"

if nginx -t 2>&1; then
    ok "Nginx config syntax is valid"
else
    err "Nginx config has ERRORS (fix before proceeding)"
fi

echo ""
info "Active Nginx sites:"
ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "  (none)"

echo ""
info "Nginx proxy_read_timeout for /api/:"
grep -r "proxy_read_timeout" /etc/nginx/sites-enabled/ 2>/dev/null || warn "No proxy_read_timeout found — SSL streaming will timeout after 60s!"

echo ""
info "Nginx proxy_buffering for /api/:"
grep -r "proxy_buffering" /etc/nginx/sites-enabled/ 2>/dev/null || warn "proxy_buffering not set — may buffer streaming response!"

# ── 6. Firewall Status ───────────────────────────────────────────────
hdr "6. Firewall & Port 80"

if command -v ufw &>/dev/null; then
    echo ""
    info "UFW status:"
    ufw status 2>/dev/null | head -20 | awk '{print "  " $0}'
    if ufw status 2>/dev/null | grep -q "80/tcp"; then
        ok "Port 80 is allowed in UFW"
    else
        warn "Port 80 NOT in UFW rules — certbot webroot challenge will FAIL"
        echo "     → Fix: ufw allow 80/tcp && ufw reload"
    fi
else
    info "UFW not installed"
fi

echo ""
info "iptables rules for port 80:"
iptables -L INPUT -n 2>/dev/null | grep ":80\|dpt:80" | awk '{print "  " $0}' | head -5
if ! iptables -L INPUT -n 2>/dev/null | grep -q "dpt:80\|:80"; then
    warn "No iptables rule allowing port 80 input"
fi

# ── 7. Certbot ───────────────────────────────────────────────────────
hdr "7. Certbot"

if command -v certbot &>/dev/null; then
    ok "Certbot is installed: $(certbot --version 2>&1)"
    echo ""
    info "Installed certificates:"
    certbot certificates 2>/dev/null | grep -E "Domains|Expiry|Status|Path" | awk '{print "  " $0}' || echo "  (none yet)"
else
    err "Certbot is NOT installed"
    echo "     → Fix: apt install certbot python3-certbot-nginx"
fi

# ── 8. DNS Check ─────────────────────────────────────────────────────
hdr "8. DNS & Public IP"

PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || curl -s --max-time 5 api.ipify.org 2>/dev/null || echo "unknown")
echo ""
ok "Server public IP: $PUBLIC_IP"
echo ""
info "To verify DNS before requesting SSL, run:"
echo "  dig +short panel.yourdomain.com"
echo "  # The result must match: $PUBLIC_IP"
echo "  # Cloudflare Proxy must be OFF (orange cloud → grey cloud)"

# ── 9. Backend Logs (last 30 lines) ─────────────────────────────────
hdr "9. Backend Logs (last 30 lines)"
journalctl -u vpnmaster-backend -n 30 --no-pager 2>/dev/null || echo "  (service logs unavailable)"

# ── 10. Nginx Error Log ──────────────────────────────────────────────
hdr "10. Nginx Error Log (last 20 lines)"
tail -n 20 /var/log/nginx/error.log 2>/dev/null || echo "  (log empty or unavailable)"

# ── Summary ──────────────────────────────────────────────────────────
hdr "Summary & Quick Fixes"

echo ""
echo -e "${BOLD}If SSL issuance fails with 'Load failed':${NC}"
echo ""
echo "  1. Copy & run the curl commands from section 4 above."
echo "     Paste the output here for diagnosis."
echo ""
echo "  2. Check section 5 — Nginx MUST have proxy_read_timeout ≥ 300s"
echo "     and proxy_buffering off for /api/ routes."
echo ""
echo "  3. After fixing Nginx config:"
echo "     nginx -t && systemctl reload nginx"
echo ""
echo "  4. Re-apply the correct Nginx config:"
echo "     bash /opt/vpn-master-panel/install.sh  (re-runs setup_nginx)"
echo "     OR manually patch /etc/nginx/sites-available/vpnmaster"
echo ""
echo "  5. Verify certbot is installed: apt install certbot python3-certbot-nginx"
echo ""

sep
echo -e "  Diagnostic complete. Paste this output for further analysis."
sep
