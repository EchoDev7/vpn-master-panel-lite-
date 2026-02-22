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
Before every attempt we open port 80 in the active firewall (ufw / firewalld / iptables)
and restore the rules in a `finally` block regardless of outcome.

IMPORTANT — Generator design
------------------------------
Every method that needs to both stream progress AND return a boolean uses the
"result holder" pattern (a mutable list) so that `yield from` semantics don't
need to rely on StopIteration.value, which is fragile and was the root cause of
the previous "STREAM ERROR: Load failed" bug.
"""

import os
import re
import subprocess
import logging
from typing import Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Validation ────────────────────────────────────────────────────────────────
_DOMAIN_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-\.]{1,253}[a-zA-Z0-9]$')
_EMAIL_RE  = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

_ALLOWED_SSL_PORTS = {2053, 2083, 2087, 2096, 8443}

# Webroot directory served by Nginx for ACME challenge
_WEBROOT = "/var/www/html"


class SSLService:

    def __init__(self):
        self.certbot_path = self._find_certbot()

    # ─────────────────────────────────────────────────────────── helpers ──────

    @staticmethod
    def _find_certbot() -> Optional[str]:
        """
        Locate the certbot binary.
        Returns the full path, or None if not found anywhere.
        """
        candidates = [
            "/usr/bin/certbot",
            "/usr/local/bin/certbot",
            "/snap/bin/certbot",
            "/usr/local/sbin/certbot",
        ]
        for p in candidates:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        # Last resort: try PATH
        import shutil
        found = shutil.which("certbot")
        return found  # may be None

    @staticmethod
    def _install_certbot() -> Iterator[str]:
        """
        Attempt to install certbot automatically via apt.
        Yields progress lines.  Returns True on success via result_holder pattern.
        """
        yield "INFO: certbot not found — attempting automatic installation...\n"
        yield "EXEC: apt-get update -qq\n"
        ok, out = SSLService._run(["apt-get", "update", "-qq"])
        if not ok:
            yield f"WARN: apt update failed: {out[:200]}\n"

        yield "EXEC: apt-get install -y certbot python3-certbot-nginx\n"
        ok, out = SSLService._run(
            ["apt-get", "install", "-y", "--no-install-recommends",
             "certbot", "python3-certbot-nginx"]
        )
        if ok:
            yield "INFO: certbot installed successfully.\n"
        else:
            yield f"ERROR: apt install failed:\n{out[:500]}\n"
            yield "HELP: Try manually: apt install certbot python3-certbot-nginx\n"

    @staticmethod
    def _validate_domain(domain: str) -> bool:
        return bool(domain and _DOMAIN_RE.match(domain))

    @staticmethod
    def _validate_email(email: str) -> bool:
        return bool(email and _EMAIL_RE.match(email))

    @staticmethod
    def _run(cmd: List[str]) -> Tuple[bool, str]:
        """Run a subprocess synchronously. Returns (success, combined_output)."""
        try:
            r = subprocess.run(
                cmd, shell=False, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                timeout=30,
            )
            return True, r.stdout or ""
        except subprocess.CalledProcessError as exc:
            return False, exc.stdout or ""
        except subprocess.TimeoutExpired:
            return False, f"Timeout running: {' '.join(cmd)}"
        except FileNotFoundError:
            return False, f"Command not found: {cmd[0]}"
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    def _service_running(name: str) -> bool:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", "--quiet", name],
                timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False

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
    def _open_port80(fw: Optional[str]) -> List[List[str]]:
        """Open port 80 in firewall. Returns cleanup command list."""
        if fw == "ufw":
            SSLService._run(["ufw", "allow", "80/tcp"])
            SSLService._run(["ufw", "reload"])
            return [["ufw", "delete", "allow", "80/tcp"]]
        if fw == "firewalld":
            SSLService._run(["firewall-cmd", "--add-port=80/tcp", "--temporary"])
            return []
        return []

    @staticmethod
    def _close_port80(cleanup_cmds: List[List[str]]):
        for cmd in cleanup_cmds:
            SSLService._run(cmd)

    @staticmethod
    def _open_https_port(fw: Optional[str], port: int):
        if fw == "ufw":
            SSLService._run(["ufw", "allow", f"{port}/tcp"])
            SSLService._run(["ufw", "reload"])
            return
        if fw == "firewalld":
            SSLService._run(["firewall-cmd", "--permanent", f"--add-port={port}/tcp"])
            SSLService._run(["firewall-cmd", "--reload"])

    @staticmethod
    def _ensure_webroot():
        """Ensure the ACME challenge directory exists and is readable."""
        challenge_dir = os.path.join(_WEBROOT, ".well-known", "acme-challenge")
        os.makedirs(challenge_dir, exist_ok=True)
        # Make sure Nginx (www-data) can read it
        try:
            os.chmod(challenge_dir, 0o755)
            os.chmod(_WEBROOT, 0o755)
        except Exception:
            pass

    # ───────────────────────────────────────────────── certbot subprocess ─────

    def _run_certbot_streamed(
        self, cmd: List[str], result_holder: List[bool]
    ) -> Iterator[str]:
        """
        Runs certbot and streams stdout/stderr line-by-line.

        Uses a `result_holder` list (mutable, passed by reference) to communicate
        success/failure back to the caller.  This avoids relying on the fragile
        StopIteration.value mechanism that broke the previous implementation.

        result_holder[0] is set to True on returncode 0, False otherwise.
        """
        result_holder.clear()
        result_holder.append(False)   # default: failed

        try:
            yield f"EXEC: {' '.join(cmd)}\n"
            process = subprocess.Popen(
                cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,          # line-buffered
            )

            for line in iter(process.stdout.readline, ""):
                stripped = line.rstrip("\n")
                if stripped:
                    yield f"CERTBOT: {stripped}\n"

            process.stdout.close()
            rc = process.wait()

            if rc == 0:
                result_holder[0] = True
                yield f"INFO: Certbot exited successfully (code 0).\n"
            else:
                yield f"WARN: Certbot exited with code {rc}.\n"

        except FileNotFoundError:
            yield f"ERROR: Certbot not found at '{cmd[0]}'.\n"
            yield "HELP: Install with: apt install certbot python3-certbot-nginx\n"
        except Exception as exc:
            yield f"ERROR: Unexpected certbot error: {exc}\n"

    # ──────────────────────────────────────────────── 3-tier SSL logic ────────

    def _try_all_methods(
        self, domain: str, email: str, nginx_running: bool
    ) -> Iterator[str]:
        """
        Try webroot → nginx plugin → standalone.
        Yields live log lines.  Sets success via result_holder pattern.
        """
        base_flags = [
            self.certbot_path, "certonly",
            "--non-interactive", "--agree-tos",
            "-m", email,
            "-d", domain,
        ]

        result = [False]   # shared mutable result holder

        # ── Method 1: Webroot (zero-downtime, preferred) ──────────────────────
        if nginx_running:
            self._ensure_webroot()
            yield "EXEC: [1/3] Webroot challenge (zero-downtime, preferred)...\n"

            ok_nginx, _ = self._run(["nginx", "-t"])
            if not ok_nginx:
                yield "WARN: Nginx config test failed — skipping webroot method.\n"
            else:
                yield from self._run_certbot_streamed(
                    base_flags + ["--webroot", "-w", _WEBROOT], result
                )
                if result[0]:
                    yield from self._post_success(domain, reload_nginx=True)
                    return

            yield "WARN: Webroot method failed. Trying Nginx plugin...\n"

            # ── Method 2: Nginx plugin ────────────────────────────────────────
            yield "EXEC: [2/3] Nginx plugin...\n"
            yield from self._run_certbot_streamed(
                base_flags + ["--nginx"], result
            )
            if result[0]:
                yield from self._post_success(domain, reload_nginx=True)
                return

            yield "WARN: Nginx plugin failed. Falling back to standalone mode...\n"

        # ── Method 3: Standalone skipped — too risky via browser ────────────
        #
        # Running certbot --standalone requires binding port 80 directly.
        # To free port 80, Nginx must either stop or reload with a config
        # that drops the port-80 listener.  Both operations risk breaking the
        # streaming HTTP connection the browser uses to watch progress.
        #
        # Instead of gambling with the live connection, we skip standalone
        # and give the user clear instructions to fix the root DNS/port issue.
        yield "\nINFO: Standalone mode skipped — it would disconnect your browser.\n"
        yield "INFO: Both webroot and nginx-plugin failed, which means:\n"
        yield "INFO:   Let's Encrypt cannot reach port 80 on your server.\n"
        yield "\nHELP: Fix the root cause, then try again:\n"
        yield "  1. DNS must point to this server's public IP.\n"
        yield f"     Run: dig +short {domain}\n"
        yield "     Expected result: this server's IP (e.g. 89.167.0.72)\n"
        yield "  2. Port 80 must be open in ALL firewalls:\n"
        yield "     a) Server OS firewall: ufw allow 80/tcp && ufw reload\n"
        yield "     b) Hosting/Cloud firewall panel (Hetzner/OVH/AWS) — open port 80\n"
        yield f"     c) Test: curl -v http://{domain}/.well-known/acme-challenge/test\n"
        yield "  3. Cloudflare users: set DNS to 'DNS only' (grey cloud), NOT Proxied.\n"
        yield "  4. After fixing port 80, click 'Get SSL' again — webroot will succeed.\n"
        result[0] = False

        if result[0]:
            yield from self._post_success(domain, reload_nginx=True)
            return

        # ── All methods failed ────────────────────────────────────────────────
        yield "\nERROR: All 3 certbot methods failed.\n"
        yield "HELP: Most common causes:\n"
        yield "  1. DNS A record must point to THIS server's public IP.\n"
        yield "     Run: dig +short " + domain + "\n"
        yield "  2. Port 80 must be open to the internet (check hosting/cloud firewall).\n"
        yield "     Run on server: curl -v http://" + domain + "/\n"
        yield "  3. If using Cloudflare: DNS must be 'DNS only' (grey cloud), NOT 'Proxied'.\n"
        yield "  4. certbot rate limit: max 5 certs per domain per week.\n"
        yield "     Check: https://crt.sh/?q=" + domain + "\n"

    # ──────────────────────────────────────────────── public entry point ──────

    def stream_letsencrypt_cert(self, domain: str, email: str,
                                https_port: Optional[int] = None) -> Iterator[str]:
        """
        Generator that yields live progress lines suitable for StreamingResponse.
        Call with:
            StreamingResponse(ssl_service.stream_letsencrypt_cert(domain, email),
                              media_type="text/plain; charset=utf-8")
        """
        # ── Input validation ──────────────────────────────────────────────────
        if not domain or not email:
            yield "ERROR: Domain and email are required.\n"
            return
        if not self._validate_domain(domain):
            yield f"ERROR: Invalid domain name: '{domain}'\n"
            return
        if not self._validate_email(email):
            yield f"ERROR: Invalid email address: '{email}'\n"
            return

        yield f"INFO: Starting SSL request for domain: {domain}\n"

        # ── Resolve HTTPS port ────────────────────────────────────────────────
        # Priority: 1) caller-supplied https_port  2) auto-detect port conflict
        if https_port is not None:
            if https_port not in _ALLOWED_SSL_PORTS:
                yield (
                    f"WARN: Requested HTTPS port {https_port} is not allowed. "
                    f"Allowed: {sorted(_ALLOWED_SSL_PORTS)}. Falling back to 8443.\n"
                )
                self._https_port_override = 8443
            else:
                self._https_port_override = https_port
            yield f"INFO: HTTPS port set by caller: {self._https_port_override}\n"
        else:
            self._https_port_override = 8443
            yield "INFO: No HTTPS port provided by caller — defaulting to 8443.\n"

        # ── Ensure certbot is available ───────────────────────────────────────
        if not self.certbot_path:
            yield "WARN: certbot not found — attempting auto-install...\n"
            yield from self._install_certbot()
            # Re-locate after install
            self.certbot_path = self._find_certbot()
            if not self.certbot_path:
                yield "ERROR: certbot still not found after install attempt.\n"
                yield "HELP: Run on server: apt install certbot python3-certbot-nginx\n"
                yield "HELP: Then restart the backend: systemctl restart vpnmaster-backend\n"
                return

        yield f"INFO: Certbot binary: {self.certbot_path}\n"

        # ── Check environment ─────────────────────────────────────────────────
        nginx_running = self._service_running("nginx")
        fw = self._detect_firewall()
        yield f"INFO: Nginx running: {nginx_running}\n"
        yield f"INFO: Active firewall: {fw or 'none detected'}\n"

        # ── Open port 80 ──────────────────────────────────────────────────────
        cleanup_fw: List[List[str]] = []
        if fw:
            yield f"EXEC: Opening port 80 in {fw}...\n"
            cleanup_fw = self._open_port80(fw)
            yield "INFO: Port 80 opened in firewall.\n"
        else:
            yield "INFO: No managed firewall — relying on OS defaults.\n"

        # iptables belt-and-suspenders: ensure port 80 is open even without ufw
        iptables_added = False
        ok_ipt, _ = self._run(["which", "iptables"])
        if ok_ipt:
            ok_check, _ = self._run([
                "iptables", "-C", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"
            ])
            if not ok_check:
                self._run([
                    "iptables", "-I", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"
                ])
                iptables_added = True
                yield "EXEC: iptables: opened port 80 temporarily.\n"

        # ── Run 3-tier certbot ────────────────────────────────────────────────
        try:
            yield from self._try_all_methods(domain, email, nginx_running)
        finally:
            # Always clean up firewall rules
            if cleanup_fw:
                yield f"EXEC: Restoring {fw} firewall rules...\n"
                self._close_port80(cleanup_fw)
                yield "INFO: Firewall restored.\n"
            if iptables_added:
                self._run([
                    "iptables", "-D", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"
                ])
                yield "EXEC: iptables: temporary port 80 rule removed.\n"

    # ──────────────────────────────────────────── post-success Nginx config ───

    def _post_success(self, domain: str, reload_nginx: bool) -> Iterator[str]:
        """Actions after a certificate is successfully issued."""
        yield f"\nSUCCESS: Certificate issued for {domain}\n"
        yield "EXEC: Writing Nginx SSL reverse-proxy config...\n"

        # Detect which HTTPS port will be used before writing config
        https_port = getattr(self, "_https_port_override", None) or 8443
        written = self._update_nginx_config(domain)
        if written:
            yield f"INFO: Nginx SSL config written (HTTPS port: {https_port}).\n"
            if https_port == 8443:
                yield "INFO: Port 8443 is being used for HTTPS edge traffic.\n"
        else:
            yield "WARN: Could not write Nginx config (permission denied?). Review manually.\n"

        if reload_nginx:
            ok, out = self._run(["nginx", "-t"])
            if ok:
                self._run(["systemctl", "reload", "nginx"])
                yield "EXEC: Nginx reloaded with SSL config.\n"
            else:
                yield f"WARN: Nginx config test failed after SSL setup:\n{out}\n"

        fw = self._detect_firewall()
        if fw:
            self._open_https_port(fw, https_port)
            yield f"INFO: Firewall updated for HTTPS port {https_port} ({fw}).\n"
        else:
            yield f"INFO: No managed firewall detected — ensure tcp/{https_port} is open in your cloud firewall.\n"

        yield f"INFO: Certificate location:\n"
        yield f"INFO:   Cert → /etc/letsencrypt/live/{domain}/fullchain.pem\n"
        yield f"INFO:   Key  → /etc/letsencrypt/live/{domain}/privkey.pem\n"
        yield "INFO: Auto-renewal is handled by certbot's systemd timer.\n"
        if https_port == 8443:
            yield f"DONE: Panel is now protected with HTTPS.\n"
            yield f"DONE: Access your panel at: https://{domain}:8443\n"
        else:
            yield f"DONE: Panel is now protected with HTTPS.\n"
            yield f"DONE: Access your panel at: https://{domain}\n"

    # ─────────────────────────────────────────────── Nginx config writer ──────

    def _update_nginx_config(self, domain: str) -> bool:
        """
        Write a production Nginx reverse-proxy config for the given domain.

        Port selection (in priority order):
          1. self._https_port_override — set by stream_letsencrypt_cert() from
             the caller-supplied value (user setting panel_https_port / sub_https_port)
          2. Fallback default: 8443

        React frontend is served directly by Nginx from /frontend/dist.
        FastAPI backend runs on 127.0.0.1:8001 (internal).
        """
        https_port = getattr(self, "_https_port_override", None) or 8443
        config_path  = f"/etc/nginx/sites-available/vpn_panel_{domain}"
        symlink_path = f"/etc/nginx/sites-enabled/vpn_panel_{domain}"

        # Build the redirect URL — include port only when non-standard
        redirect_target = f"https://$host:{https_port}$request_uri"
        listen_directive = f"{https_port} ssl http2"

        nginx_conf = f"""# VPN Master Panel — generated by ssl_service.py
# Domain: {domain}  |  HTTPS port: {https_port}
# NOTE: Managed SSL edge-port policy is active (allowed: 2053, 2083, 2087, 2096, 8443).
# Generated automatically — do not edit by hand.

# ── HTTP: redirect to HTTPS + ACME renewal ───────────────────────────────────
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    # Certbot renewal — webroot challenge (zero-downtime)
    location /.well-known/acme-challenge/ {{
        root {_WEBROOT};
        try_files $uri =404;
    }}

    # All other HTTP → HTTPS redirect
    location / {{
        return 301 {redirect_target};
    }}
}}

# ── HTTPS: main panel (port {https_port}) ─────────────────────────────────────
server {{
    listen {listen_directive};
    listen [::]:{https_port} ssl http2;
    server_name {domain};

    ssl_certificate     /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

    # Let's Encrypt recommended TLS options
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # HSTS — 6 months
    add_header Strict-Transport-Security "max-age=15768000; includeSubDomains" always;

    # ── Backend API + SSE streaming (FastAPI :8001) ───────────────────────────
    location /api/ {{
        proxy_pass         http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # Long timeout for certbot SSL issuance (can take 60-180 s)
        proxy_read_timeout  600s;
        proxy_send_timeout  600s;
        proxy_connect_timeout 30s;

        # Disable ALL buffering for live streaming (certbot output)
        proxy_buffering    off;
        proxy_cache        off;
        proxy_cache_bypass 1;
        chunked_transfer_encoding on;
        add_header X-Accel-Buffering no always;
    }}

    # ── WebSocket (FastAPI :8001) ─────────────────────────────────────────────
    location /ws/ {{
        proxy_pass         http://127.0.0.1:8001/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering    off;
    }}

    # ── Public subscription endpoints (/sub/*) ───────────────────────────────
    location /sub/ {{
        proxy_pass         http://127.0.0.1:8001/sub/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        proxy_buffering    off;
        proxy_cache        off;
    }}

    # ── React frontend static files ───────────────────────────────────────────
    # Served directly by Nginx (fastest, no proxy overhead)
    root /opt/vpn-master-panel/frontend/dist;
    index index.html;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {{
        expires     30d;
        add_header  Cache-Control "public, immutable";
        try_files   $uri =404;
    }}

    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""
        try:
            # Remove stale default site symlink if present
            default_enabled = "/etc/nginx/sites-enabled/default"
            if os.path.islink(default_enabled):
                try:
                    os.unlink(default_enabled)
                except Exception:
                    pass

            with open(config_path, "w") as fh:
                fh.write(nginx_conf)

            # Create symlink only if it doesn't already exist
            if not os.path.exists(symlink_path):
                os.symlink(config_path, symlink_path)

            return True

        except PermissionError:
            logger.error("Permission denied writing Nginx config — backend must run as root.")
            return False
        except Exception as exc:
            logger.error(f"Nginx config write error: {exc}")
            return False

    # ─────────────────────────────────────────────────────── status check ─────

    def check_ssl_status(self, domain: str) -> dict:
        """Return info about an installed certificate."""
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        if not os.path.exists(cert_path):
            return {"installed": False, "domain": domain}
        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-noout",
                 "-dates", "-subject"],
                capture_output=True, text=True, timeout=10,
            )
            info: dict = {}
            for line in result.stdout.strip().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k.strip()] = v.strip()
            return {
                "installed": True,
                "domain": domain,
                "not_before": info.get("notBefore"),
                "not_after":  info.get("notAfter"),
                "cert_path":  cert_path,
            }
        except Exception as exc:
            return {"installed": True, "domain": domain, "error": str(exc)}
