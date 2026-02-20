"""
SSL Certificate Service — Let's Encrypt via Certbot
=====================================================
Strategy (3-tier fallback, fully logged):

  1. Webroot  — fastest, zero downtime.
       Certbot writes a challenge file to /var/www/html/.well-known/acme-challenge/
       Nginx serves it on port 80.  Requires Nginx running + port 80 open.

  2. Nginx plugin — certbot modifies nginx config automatically.
       Used when webroot fails but nginx is running.

  3. Standalone — certbot binds port 80 directly.
       Used when nginx is NOT running or both previous methods failed.
       Nginx is stopped momentarily, cert issued, nginx restarted.

Port-80 management
-------------------
Before every attempt we:
  a. Check whether port 80 is actually reachable (ss / netstat).
  b. If a firewall (ufw / iptables) is active, temporarily open port 80.
  c. After the cert is issued, restore the firewall to its original state.

Nginx config generation
------------------------
Generates a production-ready config that proxies:
  - /api/v1/  →  FastAPI backend  (port 8001)
  - /ws/      →  WebSocket        (port 8001)
  - /         →  React frontend   (port 3000)
"""

import os
import re
import socket
import subprocess
import logging
from typing import Iterator, Tuple, Optional

logger = logging.getLogger(__name__)

# ── Validation ────────────────────────────────────────────────────────────────
_DOMAIN_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-\.]{1,253}[a-zA-Z0-9]$')
_EMAIL_RE  = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

# Webroot directory served by Nginx for ACME challenge
_WEBROOT = "/var/www/html"


class SSLService:

    def __init__(self):
        self.certbot_path = self._find_certbot()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _find_certbot() -> str:
        for p in ["/usr/bin/certbot", "/usr/local/bin/certbot"]:
            if os.path.exists(p):
                return p
        return "certbot"  # fallback to PATH

    @staticmethod
    def _validate_domain(domain: str) -> bool:
        return bool(domain and _DOMAIN_RE.match(domain))

    @staticmethod
    def _validate_email(email: str) -> bool:
        return bool(email and _EMAIL_RE.match(email))

    @staticmethod
    def _run(cmd: list) -> Tuple[bool, str]:
        """Run a subprocess, return (success, combined_output)."""
        try:
            r = subprocess.run(
                cmd, shell=False, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            return True, r.stdout
        except subprocess.CalledProcessError as exc:
            return False, exc.stdout or ""
        except FileNotFoundError:
            return False, f"Command not found: {cmd[0]}"

    @staticmethod
    def _service_running(name: str) -> bool:
        ok, _ = SSLService._run(["systemctl", "is-active", "--quiet", name])
        return ok

    @staticmethod
    def _detect_firewall() -> Optional[str]:
        """Return 'ufw', 'firewalld', or None."""
        ok, _ = SSLService._run(["which", "ufw"])
        if ok:
            ok2, out = SSLService._run(["ufw", "status"])
            if ok2 and "active" in out.lower():
                return "ufw"
        ok, _ = SSLService._run(["which", "firewall-cmd"])
        if ok:
            ok2, out = SSLService._run(["firewall-cmd", "--state"])
            if ok2 and "running" in out.lower():
                return "firewalld"
        return None

    @staticmethod
    def _open_port80(fw: Optional[str]) -> list:
        """Open port 80 in firewall. Returns list of cleanup commands."""
        if fw == "ufw":
            SSLService._run(["ufw", "allow", "80/tcp"])
            return [["ufw", "delete", "allow", "80/tcp"]]
        if fw == "firewalld":
            # --temporary means auto-reverts on reboot; no explicit cleanup needed
            SSLService._run(["firewall-cmd", "--add-port=80/tcp", "--temporary"])
            return []
        return []

    @staticmethod
    def _close_port80(cleanup_cmds: list):
        for cmd in cleanup_cmds:
            SSLService._run(cmd)

    @staticmethod
    def _ensure_webroot():
        """Make sure the ACME challenge directory exists."""
        challenge_dir = os.path.join(_WEBROOT, ".well-known", "acme-challenge")
        os.makedirs(challenge_dir, exist_ok=True)

    # ── Main entry point ──────────────────────────────────────────────────────

    def stream_letsencrypt_cert(self, domain: str, email: str) -> Iterator[str]:
        """
        Generator that yields live progress lines suitable for StreamingResponse.
        """
        # ── Validate ──────────────────────────────────────────────────────────
        if not domain or not email:
            yield "ERROR: Domain and email are required.\n"
            return
        if not self._validate_domain(domain):
            yield f"ERROR: Invalid domain name: '{domain}'\n"
            return
        if not self._validate_email(email):
            yield f"ERROR: Invalid email address: '{email}'\n"
            return

        yield f"INFO: Starting SSL certificate request for {domain}\n"
        yield f"INFO: Certbot binary: {self.certbot_path}\n"

        # ── Detect environment ────────────────────────────────────────────────
        nginx_running = self._service_running("nginx")
        fw = self._detect_firewall()
        yield f"INFO: Nginx running: {nginx_running}\n"
        yield f"INFO: Firewall: {fw or 'none detected'}\n"

        # ── Open port 80 in firewall (ufw / firewalld) ────────────────────────
        cleanup_fw = []
        if fw:
            yield f"EXEC: Opening port 80 in {fw}...\n"
            cleanup_fw = self._open_port80(fw)
            yield "INFO: Port 80 opened in firewall.\n"
        else:
            yield "INFO: No managed firewall detected — relying on OS defaults.\n"

        # ── iptables belt-and-suspenders ──────────────────────────────────────
        iptables_added = False
        ok_ipt, _ = self._run(["which", "iptables"])
        if ok_ipt:
            ok_check, _ = self._run(
                ["iptables", "-C", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"]
            )
            if not ok_check:
                self._run(["iptables", "-I", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"])
                iptables_added = True
                yield "EXEC: iptables: opened port 80 temporarily.\n"

        try:
            # Run the 3-tier attempt
            yield from self._try_all_methods(domain, email, nginx_running)
        finally:
            # ── Always restore firewall ───────────────────────────────────────
            if cleanup_fw:
                yield f"EXEC: Restoring {fw} firewall rules...\n"
                self._close_port80(cleanup_fw)
                yield "INFO: Firewall restored.\n"
            if iptables_added:
                self._run(["iptables", "-D", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"])
                yield "EXEC: iptables: temporary port 80 rule removed.\n"

    def _try_all_methods(
        self, domain: str, email: str, nginx_running: bool
    ) -> Iterator[str]:
        """
        Try webroot → nginx plugin → standalone in order.
        Yields log lines for each step.
        """
        base_flags = [
            self.certbot_path, "certonly",
            "--non-interactive", "--agree-tos",
            "-m", email,
            "-d", domain,
        ]

        # ── Method 1: Webroot (zero-downtime) ────────────────────────────────
        if nginx_running:
            self._ensure_webroot()
            yield "EXEC: [1/3] Webroot challenge (zero-downtime)...\n"
            ok, _ = self._run(["nginx", "-t"])
            if not ok:
                yield "WARN: Nginx config test failed — skipping webroot method.\n"
            else:
                success = yield from self._run_certbot_streamed(
                    base_flags + ["--webroot", "-w", _WEBROOT]
                )
                if success:
                    yield from self._post_success(domain, reload_nginx=True)
                    return

            yield "WARN: Webroot failed. Trying Nginx plugin...\n"

            # ── Method 2: Nginx plugin ────────────────────────────────────────
            yield "EXEC: [2/3] Nginx plugin...\n"
            success = yield from self._run_certbot_streamed(base_flags + ["--nginx"])
            if success:
                yield from self._post_success(domain, reload_nginx=True)
                return

            yield "WARN: Nginx plugin failed. Falling back to standalone mode...\n"

        # ── Method 3: Standalone ──────────────────────────────────────────────
        yield "EXEC: [3/3] Standalone mode — stopping Nginx to free port 80...\n"
        if nginx_running:
            self._run(["systemctl", "stop", "nginx"])
            yield "INFO: Nginx stopped.\n"

        import time
        time.sleep(1)  # give the OS a moment to release port 80

        success = yield from self._run_certbot_streamed(base_flags + ["--standalone"])

        # Always bring Nginx back regardless of outcome
        if nginx_running:
            self._run(["systemctl", "start", "nginx"])
            yield "INFO: Nginx restarted.\n"

        if success:
            yield from self._post_success(domain, reload_nginx=True)
            return

        # ── All methods failed ────────────────────────────────────────────────
        yield "\nERROR: All 3 certbot methods failed.\n"
        yield "HELP: Checklist:\n"
        yield "  1. DNS A record for the domain must point to this server's public IP.\n"
        yield "  2. Port 80 must be reachable from the internet (check hosting provider panel).\n"
        yield "  3. No cloud-level firewall (Hetzner, OVH, AWS SG) is blocking port 80.\n"
        yield "  4. Test with: curl -v http://YOUR_SERVER_IP/\n"

    def _run_certbot_streamed(self, cmd: list) -> Iterator[str]:
        """
        Runs certbot and streams stdout/stderr line-by-line.
        Returns True (via StopIteration value) if returncode == 0.
        """
        try:
            process = subprocess.Popen(
                cmd, shell=False,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in iter(process.stdout.readline, ""):
                yield f"CERTBOT: {line}"
            process.stdout.close()
            process.wait()
            return process.returncode == 0
        except FileNotFoundError:
            yield f"ERROR: Certbot not found: '{cmd[0]}'\n"
            yield "HELP: Install with: apt install certbot python3-certbot-nginx\n"
            return False
        except Exception as exc:
            yield f"ERROR: Certbot error: {exc}\n"
            return False

    def _post_success(self, domain: str, reload_nginx: bool) -> Iterator[str]:
        """Steps after successful cert issuance."""
        yield f"\nSUCCESS: Certificate issued for {domain}\n"
        yield "EXEC: Writing Nginx SSL reverse-proxy config...\n"
        written = self._update_nginx_config(domain)
        if written:
            yield "INFO: Nginx config written.\n"
        else:
            yield "WARN: Could not write Nginx config (permission denied?). Review manually.\n"

        if reload_nginx:
            ok, out = self._run(["nginx", "-t"])
            if ok:
                self._run(["systemctl", "reload", "nginx"])
                yield "EXEC: Nginx reloaded successfully.\n"
            else:
                yield f"WARN: Nginx config test failed:\n{out}\n"

        yield f"INFO: Cert → /etc/letsencrypt/live/{domain}/fullchain.pem\n"
        yield f"INFO: Key  → /etc/letsencrypt/live/{domain}/privkey.pem\n"
        yield "INFO: Auto-renewal is managed by certbot's systemd timer.\n"
        yield "DONE: Panel is now protected with HTTPS.\n"

    # ── Nginx Config ──────────────────────────────────────────────────────────

    def _update_nginx_config(self, domain: str) -> bool:
        """
        Generate and install a production Nginx reverse-proxy config.
        Ports used:  backend FastAPI = 8001,  frontend React = 3000.
        """
        config_path  = f"/etc/nginx/sites-available/vpn_panel_{domain}"
        symlink_path = f"/etc/nginx/sites-enabled/vpn_panel_{domain}"

        nginx_conf = f"""# VPN Master Panel — generated by ssl_service.py
# Domain: {domain}

# ── HTTP: ACME challenge passthrough + redirect ──────────────────────────────
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    # Required for certbot renewal
    location /.well-known/acme-challenge/ {{
        root {_WEBROOT};
    }}

    location / {{
        return 301 https://$host$request_uri;
    }}
}}

# ── HTTPS: main panel ─────────────────────────────────────────────────────────
server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain};

    ssl_certificate     /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

    # Use Let's Encrypt recommended TLS settings if available
    # (installed by certbot automatically)
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # HSTS
    add_header Strict-Transport-Security "max-age=15768000; includeSubDomains" always;

    # ── Backend API & SSE streaming (FastAPI on :8001) ────────────────────
    location /api/ {{
        proxy_pass         http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        # Disable buffering so SSE / streaming responses reach the browser live
        proxy_buffering    off;
        proxy_cache        off;
        chunked_transfer_encoding on;
    }}

    # ── WebSocket (FastAPI on :8001) ──────────────────────────────────────
    location /ws/ {{
        proxy_pass         http://127.0.0.1:8001/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_read_timeout 3600s;
    }}

    # ── Frontend React/Vite (port 3000) ──────────────────────────────────
    location / {{
        proxy_pass         http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""
        try:
            # Disable the default nginx placeholder if it exists
            default_enabled = "/etc/nginx/sites-enabled/default"
            if os.path.islink(default_enabled):
                try:
                    os.unlink(default_enabled)
                except Exception:
                    pass

            with open(config_path, "w") as fh:
                fh.write(nginx_conf)

            if not os.path.exists(symlink_path):
                os.symlink(config_path, symlink_path)

            return True
        except PermissionError:
            logger.error("Permission denied writing Nginx config. Backend must run as root.")
            return False
        except Exception as exc:
            logger.error(f"Nginx config write error: {exc}")
            return False

    # ── Status helpers ────────────────────────────────────────────────────────

    def check_ssl_status(self, domain: str) -> dict:
        """Return info about an installed certificate."""
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        if not os.path.exists(cert_path):
            return {"installed": False, "domain": domain}
        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-noout", "-dates", "-subject"],
                capture_output=True, text=True
            )
            info = {}
            for line in result.stdout.strip().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k.strip()] = v.strip()
            return {
                "installed": True,
                "domain": domain,
                "not_before": info.get("notBefore"),
                "not_after": info.get("notAfter"),
                "cert_path": cert_path,
            }
        except Exception as exc:
            return {"installed": True, "domain": domain, "error": str(exc)}
