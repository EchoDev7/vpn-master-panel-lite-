#!/bin/bash
USERNAME=$common_name
VPN_IP=$ifconfig_pool_remote_ip
DEV=$dev

# Get speed limit from DB (F7)
LIMIT=$(python3 /etc/openvpn/scripts/get_speed_limit.py "$USERNAME")

if [ -n "$LIMIT" ] && [ "$LIMIT" -gt "0" ]; then
    # Apply htb qdisc
    /sbin/tc qdisc add dev $DEV root handle 1: htb default 10
    /sbin/tc class add dev $DEV parent 1: classid 1:1 htb rate ${LIMIT}mbit ceil ${LIMIT}mbit
    /sbin/tc filter add dev $DEV protocol ip parent 1:0 prio 1 \
        u32 match ip dst $VPN_IP/32 flowid 1:1
fi
exit 0
