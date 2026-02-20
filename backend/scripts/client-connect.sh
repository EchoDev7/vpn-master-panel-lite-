#!/bin/bash
# Bandwidth Shaping Script
# Called by OpenVPN on client connect via: client-connect /etc/openvpn/scripts/client-connect.sh
#
# OpenVPN environment variables used:
#   $common_name              — username (from auth-user-pass / username-as-common-name)
#   $ifconfig_pool_remote_ip  — assigned VPN IP for this client
#   $dev                      — tun interface name (e.g. tun0)
#
# tc class ID strategy:
#   Use last two octets of the VPN IP to form a 16-bit class ID.
#   Supports subnets up to /16 without collision.
#   e.g. 10.8.0.5  -> CLASS_ID=5   (0*256 + 5)
#        10.8.1.5  -> CLASS_ID=261  (1*256 + 5)
#        10.8.2.5  -> CLASS_ID=517  (2*256 + 5)
#
# Filter handle persistence:
#   The kernel-assigned filter handle is stored in /run/openvpn/tc/
#   keyed by VPN IP so client-disconnect.sh can remove it cleanly.

set -euo pipefail

USERNAME="${common_name}"
VPN_IP="${ifconfig_pool_remote_ip}"
DEV="${dev}"

SCRIPT="/etc/openvpn/scripts/get_speed_limit.py"
TC_STATE_DIR="/run/openvpn/tc"
TC_LOG="/var/log/openvpn/tc.log"

# Nothing to do if speed-limit script is absent
if [ ! -f "$SCRIPT" ]; then
    exit 0
fi

# Fetch the configured speed limit (Mbps) from the database
LIMIT=$(python3 "$SCRIPT" "$USERNAME" 2>/dev/null || true)

# Skip shaping if no limit or limit is 0
if [ -z "$LIMIT" ] || [ "$LIMIT" -le 0 ] 2>/dev/null; then
    exit 0
fi

# ── Derive a collision-free class ID from the VPN IP ─────────────────────────
# Extract third and fourth octet; combine into a 16-bit integer.
OCTET3=$(echo "$VPN_IP" | cut -d. -f3)
OCTET4=$(echo "$VPN_IP" | cut -d. -f4)
CLASS_ID=$(( (OCTET3 * 256) + OCTET4 ))

# Sanity: tc class IDs must be 1–65534
if [ "$CLASS_ID" -lt 1 ] || [ "$CLASS_ID" -gt 65534 ]; then
    logger -t openvpn-tc "Invalid CLASS_ID=$CLASS_ID for VPN_IP=$VPN_IP — skipping"
    exit 0
fi

# ── Ensure HTB root qdisc exists on the tun interface ────────────────────────
if ! tc qdisc show dev "$DEV" 2>/dev/null | grep -q "root.*htb"; then
    tc qdisc add dev "$DEV" root handle 1: htb default 9999
fi

# ── Ensure a default (unlimited) class exists so unmatched traffic still flows ─
# class 1:9999 is the default catch-all (no rate limit)
tc class replace dev "$DEV" parent 1: classid 1:9999 htb rate 1000mbit ceil 1000mbit 2>/dev/null || true

# ── Add / replace the per-user HTB class ─────────────────────────────────────
tc class replace dev "$DEV" parent 1: classid "1:${CLASS_ID}" \
    htb rate "${LIMIT}mbit" ceil "${LIMIT}mbit" burst 15k

# ── Add the u32 filter that steers this VPN IP into its class ────────────────
# Use 'tc filter add' (not replace) so we get a fresh handle we can capture.
# First remove any stale filter for this IP from a previous session.
STALE_HANDLE_FILE="${TC_STATE_DIR}/${VPN_IP}.handle"
if [ -f "$STALE_HANDLE_FILE" ]; then
    STALE_HANDLE=$(cat "$STALE_HANDLE_FILE" 2>/dev/null || true)
    if [ -n "$STALE_HANDLE" ]; then
        tc filter del dev "$DEV" parent 1: handle "$STALE_HANDLE" prio 1 u32 2>/dev/null || true
    fi
    rm -f "$STALE_HANDLE_FILE"
fi

mkdir -p "$TC_STATE_DIR"

# Add the filter and capture the handle from tc output
FILTER_OUTPUT=$(tc filter add dev "$DEV" protocol ip parent 1:0 prio 1 \
    u32 match ip dst "${VPN_IP}/32" flowid "1:${CLASS_ID}" 2>&1)

# Retrieve the handle that was just assigned
FILTER_HANDLE=$(tc filter show dev "$DEV" parent 1: protocol ip prio 1 2>/dev/null \
    | awk "/match.*${VPN_IP//./\\.}\\/32/{found=1} found && /^filter/{print; found=0}" \
    | awk '{for(i=1;i<=NF;i++) if($i=="handle") print $(i+1)}' \
    | head -1)

# Persist the handle for cleanup on disconnect
if [ -n "$FILTER_HANDLE" ]; then
    echo "$FILTER_HANDLE" > "${TC_STATE_DIR}/${VPN_IP}.handle"
fi

# ── Log ───────────────────────────────────────────────────────────────────────
echo "$(date -Iseconds) CONNECT user=${USERNAME} ip=${VPN_IP} dev=${DEV} class=1:${CLASS_ID} limit=${LIMIT}Mbps handle=${FILTER_HANDLE:-unknown}" \
    >> "$TC_LOG"

exit 0
