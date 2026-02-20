#!/bin/bash
# Bandwidth Shaping Cleanup Script
# Called by OpenVPN on client disconnect via: client-disconnect /etc/openvpn/scripts/client-disconnect.sh
#
# OpenVPN environment variables used:
#   $common_name              — username
#   $ifconfig_pool_remote_ip  — VPN IP that was assigned to this client
#   $dev                      — tun interface name
#
# Cleanup order matters:
#   1. Delete the u32 filter (releases the reference to the class)
#   2. Delete the HTB class (kernel refuses to delete a class with active filters)
#
# The filter handle is read from /run/openvpn/tc/<VPN_IP>.handle
# which was written by client-connect.sh.

USERNAME="${common_name}"
VPN_IP="${ifconfig_pool_remote_ip}"
DEV="${dev}"

TC_STATE_DIR="/run/openvpn/tc"
TC_LOG="/var/log/openvpn/tc.log"

# ── Derive the same class ID used on connect ─────────────────────────────────
OCTET3=$(echo "$VPN_IP" | cut -d. -f3)
OCTET4=$(echo "$VPN_IP" | cut -d. -f4)
CLASS_ID=$(( (OCTET3 * 256) + OCTET4 ))

HANDLE_FILE="${TC_STATE_DIR}/${VPN_IP}.handle"

# ── Step 1: Delete the u32 filter ────────────────────────────────────────────
if [ -f "$HANDLE_FILE" ]; then
    FILTER_HANDLE=$(cat "$HANDLE_FILE" 2>/dev/null || true)
    if [ -n "$FILTER_HANDLE" ]; then
        tc filter del dev "$DEV" parent 1: handle "$FILTER_HANDLE" prio 1 u32 2>/dev/null || true
    fi
    rm -f "$HANDLE_FILE"
else
    # Fallback: delete by matching the destination IP (slower but safe)
    tc filter del dev "$DEV" parent 1: protocol ip prio 1 \
        u32 match ip dst "${VPN_IP}/32" 2>/dev/null || true
fi

# ── Step 2: Delete the HTB class ─────────────────────────────────────────────
# The class will only be deleted if no filters reference it any more.
tc class del dev "$DEV" parent 1: classid "1:${CLASS_ID}" 2>/dev/null || true

# ── Log ───────────────────────────────────────────────────────────────────────
echo "$(date -Iseconds) DISCONNECT user=${USERNAME} ip=${VPN_IP} dev=${DEV} class=1:${CLASS_ID}" \
    >> "$TC_LOG"

exit 0
