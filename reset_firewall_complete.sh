#!/bin/bash
# COMPLETE FIREWALL RESET SCRIPT
# This script deletes the existing UFW configuration and replaces it with a guaranteed working version.

echo "🛑 Stopping UFW..."
ufw disable

# Detect Main Network Interface
MAIN_IFACE=$(ip route | grep '^default' | awk '{print $5}' | head -n1)
if [ -z "$MAIN_IFACE" ]; then
    MAIN_IFACE="eth0"
fi
echo "📍 Detected Main Interface: $MAIN_IFACE"

echo "🗑️  Deleting old configuration..."
rm -f /etc/ufw/before.rules
# Backup just in case, but user asked for wipe
# cp /etc/ufw/before.rules /etc/ufw/before.rules.bak.$(date +%s) 2>/dev/null

echo "✍️  Writing FRESH /etc/ufw/before.rules..."
cat <<EOF > /etc/ufw/before.rules
#
# rules.before
#
# Rules that should be run before the ufw command line added rules. Custom
# rules should be added to one of these chains:
#   ufw-before-input
#   ufw-before-output
#   ufw-before-forward
#

# =========================================================
# NAT TABLE CONFIGURATION (REQUIRED FOR VPN INTERNET)
# =========================================================
*nat
:POSTROUTING ACCEPT [0:0]

# Forward traffic from ANY source to the internet interface ($MAIN_IFACE)
# User requested 0.0.0.0/0 (General NAT) for stability
-A POSTROUTING -o $MAIN_IFACE -j MASQUERADE
COMMIT

# =========================================================
# FILTER TABLE CONFIGURATION
# =========================================================
*filter
:ufw-before-input - [0:0]
:ufw-before-output - [0:0]
:ufw-before-forward - [0:0]
:ufw-not-local - [0:0]

# Don't delete these required lines, otherwise there will be errors
-A ufw-before-input -i lo -j ACCEPT
-A ufw-before-output -o lo -j ACCEPT

# allow link-local
-A ufw-before-input -s 224.0.0.0/4 -j ACCEPT
-A ufw-before-input -d 224.0.0.0/4 -j ACCEPT

# allow dhcp client to work
-A ufw-before-input -p udp --sport 67 --dport 68 -j ACCEPT

# allow broadcast
-A ufw-before-input -d 255.255.255.255 -j ACCEPT

# quickly process packets for which we already have a connection
-A ufw-before-input -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A ufw-before-output -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A ufw-before-forward -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Setup routing allow for OpenVPN
-A ufw-before-forward -i tun0 -j ACCEPT
-A ufw-before-forward -i $MAIN_IFACE -o tun0 -j ACCEPT

COMMIT
EOF

echo "🔧 Configuring UFW Defaults..."
sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw
sed -i 's/DEFAULT_FORWARD_POLICY="REJECT"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw
sed -i 's/IPV6=yes/IPV6=no/g' /etc/default/ufw # Disable IPv6 to reduce complexity if needed

echo "🔓 Opening Ports..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw allow 3000/tcp
ufw allow 1194/udp
ufw allow 51820/udp

echo "🚀 Enabling Sysctl Forwarding..."
sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-openvpn.conf
sysctl -p /etc/sysctl.d/99-openvpn.conf

echo "✅ Starting Firewall..."
ufw default allow routed
ufw --force enable
ufw reload

echo "🔍 Verifying NAT Rules..."
iptables -t nat -L POSTROUTING -v -n
