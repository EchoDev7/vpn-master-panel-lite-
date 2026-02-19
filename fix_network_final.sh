#!/bin/bash
# Final Network Fix - Flush NAT and Setup clean rules

MAIN_IFACE=$(ip route | grep '^default' | awk '{print $5}' | head -n1)
VPN_SUBNET="10.8.0.0/24"

echo "Main Interface: $MAIN_IFACE"
echo "VPN Subnet: $VPN_SUBNET"

echo "1. Flushing existing NAT rules..."
iptables -t nat -F
iptables -t nat -X

echo "2. Applying clean NAT Masquerade rule..."
iptables -t nat -A POSTROUTING -s $VPN_SUBNET -o $MAIN_IFACE -j MASQUERADE

echo "3. Saving iptables rules (persistence)..."
netfilter-persistent save

echo "4. Checking Packet Forwarding..."
sysctl -w net.ipv4.ip_forward=1
echo 1 > /proc/sys/net/ipv4/ip_forward

echo "5. Verifying UFW Configuration..."
# We need to make sure UFW doesn't step on us, or we configure UFW correctly.
# Ideally we use UFW rules, but if they are duplicated, we clean them.

# Clean UFW before.rules of duplications
sed -i '/-A POSTROUTING -s 10.0.0.0\/8/d' /etc/ufw/before.rules
sed -i '/-A POSTROUTING -s 10.8.0.0\/8/d' /etc/ufw/before.rules
sed -i '/-A POSTROUTING -s 10.8.0.0\/24/d' /etc/ufw/before.rules

# Add fresh rule
if ! grep -q "*nat" /etc/ufw/before.rules; then
    cat <<EOT >> /etc/ufw/before.rules
*nat
:POSTROUTING ACCEPT [0:0]
-A POSTROUTING -s $VPN_SUBNET -o $MAIN_IFACE -j MASQUERADE
COMMIT
EOT
else
    # Inject before COMMIT if *nat exists but rule missing (regex is hard here, simplistic append if missing)
    if ! grep -q "$VPN_SUBNET" /etc/ufw/before.rules; then
         sed -i "/COMMIT/i -A POSTROUTING -s $VPN_SUBNET -o $MAIN_IFACE -j MASQUERADE" /etc/ufw/before.rules
    fi
fi

ufw reload
echo "Done. Testing NAT table:"
iptables -t nat -L POSTROUTING -v -n
