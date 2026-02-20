#!/usr/bin/python3
"""
OpenVPN auth-user-pass-verify script (via-file mode)
=====================================================
Called by OpenVPN as:
    auth-user-pass-verify /etc/openvpn/scripts/auth.py via-file

OpenVPN writes a temp file containing:
    line 1: username
    line 2: password

This script:
  1. Reads username/password from the temp file
  2. Queries the panel's SQLite DB for the user
  3. Verifies bcrypt password hash
  4. Checks user status (active, not expired, data limit not exceeded)
  5. Exits 0 (allow) or 1 (deny)

Install path (managed by install.sh / update.sh):
    /etc/openvpn/scripts/auth.py
"""

import sys
import os
import sqlite3
import logging

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE = "/var/log/openvpn/auth.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("openvpn-auth")

# ── DB path ───────────────────────────────────────────────────────────────────
# Primary production path (set by install.sh)
DB_CANDIDATES = [
    "/opt/vpn-master-panel/vpnmaster_lite.db",
    "/opt/vpn-master-panel/backend/vpnmaster_lite.db",
]

def _find_db() -> str:
    for path in DB_CANDIDATES:
        if os.path.exists(path):
            return path
    # Fallback: relative to this script's location (dev/test)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.join(script_dir, "..", "..", "vpnmaster_lite.db")
    fallback = os.path.normpath(fallback)
    return fallback


def _deny(reason: str, username: str = ""):
    logger.warning("DENY user=%s reason=%s", username, reason)
    sys.exit(1)


def _allow(username: str):
    logger.info("ALLOW user=%s", username)
    sys.exit(0)


def main():
    # OpenVPN passes the temp-file path as the first argument (via-file mode)
    if len(sys.argv) < 2:
        _deny("No temp-file argument provided")

    tmp_file = sys.argv[1]

    # ── Read credentials from temp file ──────────────────────────────────────
    try:
        with open(tmp_file, "r") as fh:
            lines = fh.read().splitlines()
    except Exception as exc:
        _deny(f"Cannot read temp file: {exc}")

    if len(lines) < 2:
        _deny("Temp file has fewer than 2 lines")

    username = lines[0].strip()
    password = lines[1].strip()

    if not username or not password:
        _deny("Empty username or password", username)

    # ── Connect to SQLite ─────────────────────────────────────────────────────
    db_path = _find_db()
    if not os.path.exists(db_path):
        logger.error("DB not found at %s", db_path)
        _deny("DB not found", username)

    try:
        conn = sqlite3.connect(db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as exc:
        logger.error("DB connect error: %s", exc)
        _deny("DB connect error", username)

    # ── Fetch user row ────────────────────────────────────────────────────────
    try:
        cur.execute(
            """
            SELECT hashed_password, status, expiry_date,
                   data_limit_gb, total_upload_bytes, total_download_bytes,
                   openvpn_enabled
            FROM users
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        )
        row = cur.fetchone()
    except Exception as exc:
        logger.error("DB query error for user=%s: %s", username, exc)
        conn.close()
        _deny("DB query error", username)
    finally:
        conn.close()

    if row is None:
        _deny("User not found", username)

    # ── Check openvpn_enabled ─────────────────────────────────────────────────
    if not row["openvpn_enabled"]:
        _deny("OpenVPN disabled for user", username)

    # ── Check status ──────────────────────────────────────────────────────────
    status = (row["status"] or "").lower()
    if status != "active":
        _deny(f"Account status={status}", username)

    # ── Check expiry ──────────────────────────────────────────────────────────
    expiry_str = row["expiry_date"]
    if expiry_str:
        from datetime import datetime, timezone
        try:
            # SQLite may store as "YYYY-MM-DD HH:MM:SS.ffffff" or with "+00:00"
            expiry_str_clean = expiry_str.replace("+00:00", "").strip()
            expiry_dt = datetime.fromisoformat(expiry_str_clean).replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expiry_dt:
                _deny("Account expired", username)
        except Exception as exc:
            logger.warning("Could not parse expiry_date=%s for user=%s: %s", expiry_str, username, exc)
            # Do not deny on parse failure — err on the side of leniency

    # ── Check data limit ──────────────────────────────────────────────────────
    data_limit_gb = row["data_limit_gb"] or 0.0
    if data_limit_gb > 0:
        upload = row["total_upload_bytes"] or 0
        download = row["total_download_bytes"] or 0
        used_gb = (upload + download) / (1024 ** 3)
        if used_gb >= data_limit_gb:
            _deny(f"Data limit exceeded ({used_gb:.2f}/{data_limit_gb} GB)", username)

    # ── Verify password ───────────────────────────────────────────────────────
    hashed = row["hashed_password"]
    if not hashed:
        _deny("No password hash stored", username)

    try:
        import passlib.context  # type: ignore
        pwd_context = passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")
        if not pwd_context.verify(password, hashed):
            _deny("Invalid password", username)
    except ImportError:
        # Fallback: try bcrypt directly if passlib is unavailable
        try:
            import bcrypt  # type: ignore
            if not bcrypt.checkpw(password.encode(), hashed.encode()):
                _deny("Invalid password", username)
        except ImportError:
            logger.error("Neither passlib nor bcrypt is available in the Python environment.")
            _deny("Auth library missing", username)

    _allow(username)


if __name__ == "__main__":
    main()
