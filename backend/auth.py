#!/usr/bin/python3
"""
OpenVPN Auth Script
====================
Called by OpenVPN via: auth-user-pass-verify /etc/openvpn/scripts/auth.sh via-file

Reads a temp file containing:
  line 1: username
  line 2: password

Validates against the SQLite database and exits with 0 (success) or 1 (failure).

Security notes:
  - Uses parameterised queries only — no SQL injection possible
  - Password verified with bcrypt constant-time compare
  - Connection limit checked against live management socket
  - Expiry compared in UTC, timezone-aware
"""
import sys
import os
import logging
import sqlite3
from datetime import datetime, timezone

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="/var/log/openvpn/auth.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ── Database path ─────────────────────────────────────────────────────────
_DB_CANDIDATES = [
    "/opt/vpn-master-panel/vpnmaster_lite.db",
    "/opt/vpn-master-panel/backend/vpnmaster_lite.db",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "vpnmaster_lite.db",
    ),
]


def _resolve_db_path() -> str:
    # Prefer a DB file that actually contains the expected users table.
    for path in _DB_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            with sqlite3.connect(path, timeout=1) as conn:
                row = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
                ).fetchone()
                if row:
                    return path
        except Exception:
            continue

    # Fallback: first existing path, else canonical default.
    return next((p for p in _DB_CANDIDATES if os.path.exists(p)), _DB_CANDIDATES[0])


DB_PATH = _resolve_db_path()


def _count_active_sessions(username: str) -> int:
    """
    Query the OpenVPN management socket for the number of active sessions
    belonging to *username*.  Returns 0 on any error (fail-open).
    """
    import socket as _socket

    try:
        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(("127.0.0.1", 7505))
            s.recv(1024)  # consume banner
            s.sendall(b"status 2\n")

            resp = b""
            while True:
                chunk = s.recv(8192)
                if not chunk:
                    break
                resp += chunk
                if b"\nEND" in resp or b"ERROR" in resp:
                    break
            s.sendall(b"quit\n")

        count = 0
        for line in resp.decode(errors="ignore").splitlines():
            if not line.startswith("CLIENT_LIST,") or "Common Name" in line:
                continue
            parts = line.split(",")
            # parts[1]=Common Name, parts[9]=Username (auth-user-pass value)
            cn      = parts[1].strip() if len(parts) > 1 else ""
            auth_un = parts[9].strip() if len(parts) > 9 else ""
            if cn == username or auth_un == username:
                count += 1
        return count

    except Exception as exc:
        logging.warning(f"Connection limit check failed (fail-open): {exc}")
        return 0


def auth_user(username: str, password: str) -> bool:
    """
    Authenticate *username* / *password* against the database.

    Checks (in order):
      1. User exists
      2. Status == 'active'
      3. Not expired (UTC-aware comparison)
      4. Connection limit not exceeded
      5. Password bcrypt match
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from passlib.context import CryptContext

    client_ip = os.environ.get("untrusted_ip", "unknown")
    pwd_ctx   = CryptContext(schemes=["bcrypt"], deprecated="auto")

    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()

    try:
        row = db.execute(
            text(
                "SELECT hashed_password, status, expiry_date, connection_limit "
                "FROM users WHERE username = :u"
            ),
            {"u": username},
        ).fetchone()

        if not row:
            logging.warning(f"AUTH_FAILED user_not_found username={username} ip={client_ip}")
            return False

        hashed_pw, status, expiry_raw, conn_limit = row

        # ── Status check ─────────────────────────────────────────────
        if str(status).lower() != "active":
            logging.warning(
                f"AUTH_FAILED status={status} username={username} ip={client_ip}"
            )
            return False

        # ── Expiry check (UTC, timezone-aware) ───────────────────────
        if expiry_raw:
            try:
                expiry_str = str(expiry_raw).strip().rstrip("Z")
                expiry_str = expiry_str.replace("T", " ")
                # Remove sub-second precision if present
                if "." in expiry_str:
                    expiry_str = expiry_str.split(".")[0]
                expiry_dt = datetime.fromisoformat(expiry_str).replace(tzinfo=timezone.utc)
                now_utc   = datetime.now(tz=timezone.utc)
                if now_utc > expiry_dt:
                    logging.warning(
                        f"AUTH_FAILED expired username={username} expiry={expiry_dt.isoformat()}"
                    )
                    return False
            except ValueError as exc:
                logging.error(
                    f"AUTH_ERROR bad_expiry_format username={username} "
                    f"raw={expiry_raw!r} err={exc}"
                )
                return False  # fail-safe: reject if we cannot parse expiry

        # ── Connection limit check ───────────────────────────────────
        limit = int(conn_limit) if conn_limit else 0
        if limit > 0:
            active = _count_active_sessions(username)
            if active >= limit:
                logging.warning(
                    f"AUTH_FAILED conn_limit username={username} "
                    f"active={active} limit={limit}"
                )
                return False

        # ── Password verification ────────────────────────────────────
        if pwd_ctx.verify(password, hashed_pw):
            logging.info(f"AUTH_SUCCESS username={username} ip={client_ip}")
            return True
        else:
            logging.warning(
                f"AUTH_FAILED wrong_password username={username} ip={client_ip}"
            )
            return False

    except Exception as exc:
        logging.error(f"AUTH_ERROR username={username} err={exc}")
        return False
    finally:
        db.close()
        engine.dispose()


# ── Entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Missing credentials file argument")
        sys.exit(1)

    cred_file = sys.argv[1]

    try:
        with open(cred_file) as fh:
            lines = fh.read().splitlines()
            uname = lines[0].strip() if len(lines) > 0 else ""
            pwd   = lines[1].strip() if len(lines) > 1 else ""

        if not uname or not pwd:
            logging.error("Empty username or password in credentials file")
            sys.exit(1)

        sys.exit(0 if auth_user(uname, pwd) else 1)

    except OSError as exc:
        logging.error(f"Cannot read credentials file {cred_file!r}: {exc}")
        sys.exit(1)
