#!/bin/bash
# VPN Connectivity Debugger

echo "=== 1. Kernel Forwarding ==="
sysctl net.ipv4.ip_forward
# Check if UFW overrides allowed
grep "DEFAULT_FORWARD_POLICY" /etc/default/ufw

echo -e "\n=== 2. NAT Table (Masquerading) ==="
iptables -t nat -L POSTROUTING -v -n

echo -e "\n=== 3. OpenVPN Gateway Push ==="
grep "redirect-gateway" /etc/openvpn/server.conf

echo -e "\n=== 4. DNS Push ==="
grep "dhcp-option DNS" /etc/openvpn/server.conf

echo -e "\n=== 5. Interfaces ==="
ip -br addr
