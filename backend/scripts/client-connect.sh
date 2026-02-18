#!/bin/bash
# F7: Bandwidth Shaping Script
# Called by OpenVPN on client connect

USERNAME=$common_name
VPN_IP=$ifconfig_pool_remote_ip
DEV=$dev

# Ensure python script is executable/reachable
SCRIPT="/etc/openvpn/scripts/get_speed_limit.py"
if [ ! -f "$SCRIPT" ]; then
    exit 0
fi

# Get speed limit from DB (Mbps)
LIMIT=$(python3 "$SCRIPT" "$USERNAME")

if [ -n "$LIMIT" ] && [ "$LIMIT" -gt "0" ]; then
    # Traffic Control (tc)
    # Clear existing rules for this IP (if any - hard with simple tc, better to clear on disconnect)
    # But usually this is per-interface (tun0), so we need class-based queueing
    
    # We assume 'dev' is the shared tun interface.
    # If so, we need to add a class for this user.
    # The user provided snippet assumes valid tc setup.
    # We wrap in try block to avoid erroring out connection
    
    # Check if root qdisc exists, if not add it
    tc qdisc show dev $DEV | grep -q "root" || tc qdisc add dev $DEV root handle 1: htb default 10
    
    # We need a unique class ID. Using last byte of IP or similar.
    # VPN_IP is like 10.8.0.XYZ
    CLASS_ID=$(echo $VPN_IP | awk -F. '{print $4}')
    
    # Add class with limit
    tc class replace dev $DEV parent 1: classid 1:$CLASS_ID htb rate ${LIMIT}mbit ceil ${LIMIT}mbit
    
    # Add filter to direct traffic for this IP to this class
    tc filter replace dev $DEV protocol ip parent 1:0 prio 1 \
        u32 match ip dst $VPN_IP/32 flowid 1:$CLASS_ID
        
    # LOG
    echo "$(date) Bandwidth limit ${LIMIT}Mbps applied for $USERNAME ($VPN_IP)" >> /var/log/openvpn/tc.log
fi

exit 0
