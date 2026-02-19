from fastapi import APIRouter, Depends, BackgroundTasks
from typing import Dict, Any, List
import subprocess
import shutil
import logging
import os
import re
import time
import datetime
import platform
from ..utils.security import get_current_admin
from ..models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

def get_package_version(package: str) -> Dict[str, str]:
    """
    Get installed and latest available version of a package using apt-cache policy.
    Returns: {"installed": "...", "latest": "..."}
    """
    try:
        # Run apt-cache policy
        result = subprocess.run(
            ["apt-cache", "policy", package], 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            return {"installed": "Unknown", "latest": "Unknown"}
        
        output = result.stdout
        installed = "Not Installed"
        latest = "Unknown"
        
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith("Installed:"):
                installed = line.replace("Installed:", "").strip()
                if installed == "(none)":
                    installed = "Not Installed"
            elif line.startswith("Candidate:"):
                latest = line.replace("Candidate:", "").strip()
                
        return {"installed": installed, "latest": latest}
    except Exception as e:
        logger.error(f"Error checking version for {package}: {e}")
        return {"installed": "Error", "latest": "Error"}

def get_command_version(cmd: str, arg: str = "--version") -> str:
    """Get version from command output"""
    try:
        if not shutil.which(cmd):
            return "Not Installed"
        
        result = subprocess.run(
            [cmd, arg], 
            capture_output=True, 
            text=True
        )
        # Parse first line usually
        return result.stdout.split('\n')[0].strip()
    except:
        return "Unknown"

@router.get("/full")
async def get_full_diagnostics(
    current_admin: User = Depends(get_current_admin)
):
    """
    Get comprehensive system diagnostics.
    """
    import psutil
    
    try:
        # Initialize variables that might be used in the final return but could fail earlier
        system_stats = {}
        package_status = []
        service_status = []
        rec_status = []
        branch, commit, msg, changes = "Unknown", "Unknown", "Unknown", 0
        network_stats = {}
        vpn_security = {}
        log_analysis = []
        db_health = {"status": "Unknown", "details": []}

        # 1. System Resources
        try:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            try:
                load = psutil.getloadavg()
            except AttributeError:
                load = (0, 0, 0)
            
            try:
                with open("/etc/os-release") as f:
                    os_info = {}
                    for line in f:
                        if "=" in line:
                            k,v = line.strip().split("=", 1)
                            os_info[k] = v.strip('"')
                    os_name = os_info.get("PRETTY_NAME", "Unknown Linux")
            except:
                os_name = "Unknown Linux"
                
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_str = str(datetime.timedelta(seconds=int(uptime_seconds)))
            
            system_stats = {
                "os": os_name,
                "kernel": platform.release(),
                "uptime": uptime_str,
                "load_avg": list(load),
                "memory": {
                    "used_mb": round(mem.used / 1024 / 1024, 2),
                    "total_mb": round(mem.total / 1024 / 1024, 2),
                    "percent": mem.percent
                },
                "disk": {
                    "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                    "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                    "percent": disk.percent
                }
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            system_stats = {
                "os": "Unknown",
                "kernel": "Unknown",
                "uptime": "Unknown",
                "load_avg": [0, 0, 0],
                "memory": {"used_mb": 0, "total_mb": 0, "percent": 0},
                "disk": {"used_gb": 0, "total_gb": 0, "percent": 0}
            }
        
        # 2. Package Versions
        try:
            packages = ["openvpn", "nginx", "python3", "pip", "node", "npm", "git", "curl", "ufw", "wg", "sqlite3"]
            
            for pkg in packages:
                try:
                    if pkg in ["openvpn", "nginx", "git", "curl", "ufw", "sqlite3"]:
                        versions = get_package_version(pkg)
                        package_status.append({
                            "name": pkg,
                            "installed": versions["installed"],
                            "latest": versions["latest"],
                            "status": "Update Available" if versions["installed"] != versions["latest"] and versions["installed"] != "Not Installed" else "Up to date"
                        })
                    elif pkg == "python3":
                         versions = get_package_version("python3")
                         cmd_ver = get_command_version("python3")
                         package_status.append({
                             "name": "python3",
                             "installed": cmd_ver,
                             "latest": versions["latest"],
                             "status": "OK"
                         })
                    elif pkg == "pip":
                         cmd_ver = get_command_version("pip")
                         package_status.append({
                             "name": "pip",
                             "installed": cmd_ver,
                             "latest": "Check Manually",
                             "status": "OK"
                         })
                    elif pkg == "node":
                         versions = get_package_version("nodejs")
                         cmd_ver = get_command_version("node", "-v")
                         package_status.append({
                             "name": "node",
                             "installed": cmd_ver,
                             "latest": versions["latest"],
                             "status": "OK"
                         })
                    elif pkg == "npm":
                         cmd_ver = get_command_version("npm", "-v")
                         package_status.append({
                             "name": "npm",
                             "installed": cmd_ver,
                             "latest": "Check Manually", 
                             "status": "OK"
                         })
                    elif pkg == "wg":
                         versions = get_package_version("wireguard")
                         package_status.append({
                             "name": "wireguard",
                             "installed": versions["installed"],
                             "latest": versions["latest"],
                             "status": "Update Available" if versions["installed"] != versions["latest"] and versions["installed"] != "Not Installed" else "OK"
                         })
                except Exception as e:
                    logger.error(f"Error checking package {pkg}: {e}")
                    package_status.append({"name": pkg, "installed": "Error", "latest": "Error", "status": "Error"})
        except Exception as e:
            logger.error(f"Error in package section: {e}")

        # 3. Service Status
        try:
            services = ["vpnmaster-backend", "nginx", "openvpn@server", "wg-quick@wg0", "ufw"]
            for svc in services:
                try:
                    active = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True).stdout.strip() == "active"
                    failed = subprocess.run(["systemctl", "is-failed", svc], capture_output=True, text=True).stdout.strip() == "failed"
                    
                    status_code = "Running" if active else "Stopped"
                    if failed: status_code = "Failed"
                    
                    service_status.append({
                        "name": svc,
                        "status": status_code,
                        "active": active
                    })
                except:
                    service_status.append({"name": svc, "status": "Unknown", "active": False})
        except Exception as e:
            logger.error(f"Error in service section: {e}")

        # 4. Recommended Tools
        try:
            recommendations = [
                {"name": "htop", "desc": "Interactive process viewer", "cmd": "htop"},
                {"name": "iftop", "desc": "Network bandwith monitor (interface level)", "cmd": "iftop"},
                {"name": "fail2ban", "desc": "Intrusion prevention framework", "cmd": "fail2ban-client"},
                {"name": "jq", "desc": "Command-line JSON processor", "cmd": "jq"},
                {"name": "speedtest-cli", "desc": "Internet speed measurement", "cmd": "speedtest"},
                {"name": "tree", "desc": "Recursive directory listing", "cmd": "tree"},
            ]
            
            for tool in recommendations:
                installed = shutil.which(tool["cmd"]) is not None
                rec_status.append({
                    "name": tool["name"],
                    "description": tool["desc"],
                    "installed": installed
                })
        except Exception as e:
            logger.error(f"Error in tools section: {e}")

        # 5. Project Info
        try:
            cwd = "/opt/vpn-master-panel"
            if not os.path.exists(cwd):
                cwd = "." # Fallback
                
            branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=cwd).stdout.strip() or "Unknown"
            commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=cwd).stdout.strip() or "Unknown"
            msg = subprocess.run(["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True, cwd=cwd).stdout.strip() or "No commit message"
            
            status_output = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=cwd).stdout.strip()
            changes = len(status_output.split('\n')) if status_output else 0
            
        except Exception as e:
             logger.error(f"Error getting git info: {e}")
             branch, commit, msg, changes = "Unknown", "Unknown", "Unknown", 0

        # 6. Network & Connectivity
        try:
            # Public IPs
            public_ipv4 = subprocess.run(["curl", "-4", "-s", "--max-time", "2", "ifconfig.me"], capture_output=True, text=True).stdout.strip() or "Unknown"
            public_ipv6 = subprocess.run(["curl", "-6", "-s", "--max-time", "2", "-H", "User-Agent: curl", "ipv6.icanhazip.com"], capture_output=True, text=True).stdout.strip() or "Not Detected"
            
            # Latency
            latency = "Timeout"
            try:
                latency_out = subprocess.run(["ping", "-c", "1", "8.8.8.8"], capture_output=True, text=True).stdout
                match = re.search(r"time=([\d\.]+)", latency_out)
                if match:
                    latency = match.group(1) + "ms"
            except:
                pass
                
            # Active Ports (Netstat/SS)
            listening_ports = []
            try:
                if shutil.which("netstat"):
                    cmd = ["netstat", "-tulnp"]
                    col_idx = 3 # 4th column is Local Address
                else:
                    cmd = ["ss", "-tulnp"]
                    col_idx = 4 # 5th column
                    
                out = subprocess.run(cmd, capture_output=True, text=True).stdout
                for line in out.splitlines():
                    if "LISTEN" in line or "udp" in line:
                        parts = line.split()
                        if len(parts) > col_idx:
                            addr = parts[col_idx]
                            # Simple cleanup
                            listening_ports.append(addr)
            except:
                listening_ports = ["Error fetching ports"]
                
            # Firewall
            ufw_status = "Unknown"
            if shutil.which("ufw"):
                 ufw_check = subprocess.run(["ufw", "status"], capture_output=True, text=True).stdout
                 if "Status: active" in ufw_check:
                     rule_count = ufw_check.count("[") 
                     ufw_status = f"Active ({rule_count} rules)"
                 else:
                     ufw_status = "Inactive"
                     
            network_stats = {
                "public_ipv4": public_ipv4,
                "public_ipv6": public_ipv6,
                "latency": latency,
                "listening_ports": list(set(listening_ports)),
                "firewall_status": ufw_status
            }
        except Exception as e:
            logger.error(f"Error in network section: {e}")
            network_stats = {}

        # 7. VPN Security & Certs
        try:
            # TUN
            tun_status = os.path.exists("/dev/net/tun")
            
            # IP Forwarding
            ip_fwd = False
            try:
                with open("/proc/sys/net/ipv4/ip_forward", "r") as f:
                    ip_fwd = f.read().strip() == "1"
            except:
                pass
                
            # Cert Expiry
            cert_expiry = "Unknown"
            if os.path.exists("/etc/openvpn/server.crt"):
                try:
                    cert_out = subprocess.run(["openssl", "x509", "-enddate", "-noout", "-in", "/etc/openvpn/server.crt"], capture_output=True, text=True).stdout
                    if "=" in cert_out:
                        cert_expiry = cert_out.split("=")[1].strip()
                except:
                    pass
                    
            vpn_security = {
                "tun_available": tun_status,
                "ip_forwarding": ip_fwd,
                "cert_expiry": cert_expiry
            }
        except Exception as e:
             logger.error(f"Error in vpn security section: {e}")

        # 8. Intelligent Log Analysis
        try:
            error_patterns = {
                "private key password verification failed": {"level": "CRITICAL", "msg": "PKI Key Encrypted/Corrupt", "fix": "Run './update.sh' to force-regenerate keys."},
                "Address already in use": {"level": "CRITICAL", "msg": "Port Conflict", "fix": "Check if another service is using the port (netstat -tulnp)."},
                "Options error": {"level": "ERROR", "msg": "Configuration Syntax Error", "fix": "Check server.conf for invalid directives."},
                "Permission denied": {"level": "ERROR", "msg": "File Permission Issue", "fix": "Run 'chown -R root:root /etc/openvpn' or check AppArmor."},
                "CRL: cannot read": {"level": "WARN", "msg": "CRL File Missing/Unreadable", "fix": "Regenerate CRL or check permissions."}
            }
            
            # Reading last 50 lines of journalctl for services is safer
            cmd_ovpn = ["journalctl", "-u", "openvpn@server", "-n", "50", "--no-pager"]
            cmd_back = ["journalctl", "-u", "vpnmaster-backend", "-n", "50", "--no-pager"]
            
            logs_to_scan = ""
            try:
                logs_to_scan += subprocess.run(cmd_ovpn, capture_output=True, text=True).stdout or ""
                logs_to_scan += subprocess.run(cmd_back, capture_output=True, text=True).stdout or ""
            except:
                pass

            # Check if OpenVPN is currently running
            is_ovpn_running = False
            try:
                is_ovpn_running = subprocess.run(["systemctl", "is-active", "openvpn@server"], capture_output=True, text=True).stdout.strip() == "active"
            except:
                pass
            
            logs_found = False
            # Only process if we have logs
            if logs_to_scan:
                lines = logs_to_scan.splitlines()
                # Find index of last successful start
                last_success_idx = -1
                for i, line in enumerate(lines):
                    if "Initialization Sequence Completed" in line:
                        last_success_idx = i
                
                for i, line in enumerate(lines):
                    # If we found a success message, ignore errors before it
                    if last_success_idx != -1 and i < last_success_idx:
                        continue

                    for pattern, info in error_patterns.items():
                        if pattern in line:
                            # If service is running, ignore known "Startup Fatal" errors that might be stale
                            if is_ovpn_running and info["level"] in ["CRITICAL", "ERROR"]:
                                continue

                            issue_msg = info["msg"]
                            # Avoid duplicates
                            if not any(i['message'] == issue_msg for i in log_analysis):
                                log_analysis.append({
                                    "level": info["level"],
                                    "message": issue_msg,
                                    "fix": info["fix"],
                                    "log_snippet": line[:100] + "..."
                                })
                                logs_found = True
                                
            if not logs_found:
                 log_analysis = [{"level": "OK", "message": "No critical error patterns detected.", "fix": ""}]
                 
        except Exception as e:
            logger.error(f"Error in log analysis: {e}")
            log_analysis = [{"level": "ERROR", "message": f"Failed to analyze logs: {str(e)}", "fix": ""}]

        # 9. Deep Database Check
        try:
            from ..database import SessionLocal
            from sqlalchemy import text
            
            db = SessionLocal()
            try:
                # Integrity
                res = db.execute(text("PRAGMA integrity_check")).fetchone()[0]
                integrity = "OK" if res == "ok" else "FAIL"
                db_health["integrity"] = integrity
                
                # Tables
                tables = ["users", "settings", "vpn_servers", "traffic_logs"]
                existing = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
                existing_names = [r[0] for r in existing]
                missing = [t for t in tables if t not in existing_names]
                
                if missing:
                    db_health["status"] = "FAIL"
                    db_health["missing_tables"] = missing
                else:
                    db_health["status"] = "OK"
                    
                # Admin check
                admin = db.execute(text("SELECT username FROM users WHERE role IN ('SUPER_ADMIN', 'ADMIN', 'super_admin', 'admin')")).fetchone()
                db_health["admin_user"] = admin[0] if admin else "MISSING"
                
            except Exception as e:
                db_health["status"] = "ERROR"
                db_health["error"] = str(e)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in DB check: {e}")
            
        # 10. API Health Check
        api_health = []
        try:
            api_base = "http://127.0.0.1:8001"
            endpoints = [
                "/api/health", 
                "/docs"
            ]
            
            import asyncio
            
            for ep in endpoints:
                try:
                    # Async subprocess to avoid blocking the event loop
                    proc = await asyncio.create_subprocess_exec(
                        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{api_base}{ep}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    try:
                        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3.0)
                        code = stdout.decode().strip()
                    except asyncio.TimeoutError:
                        code = "000"
                        try:
                            proc.kill()
                        except:
                            pass
                    
                    status = "Unreachable"
                    if code in ["200", "307", "401", "403", "405"]:
                        status = "Available" if code in ["200", "307"] else "Secure/Active"
                        
                    api_health.append({
                        "endpoint": ep,
                        "status": status,
                        "code": code
                    })
                except Exception as e:
                    api_health.append({"endpoint": ep, "status": "Unreachable", "code": "000"})
        except Exception as e:
            logger.error(f"Error in API health check: {e}")

        # 11. Raw Logs (Last 20 Lines)
        raw_logs = {"openvpn": [], "backend": []}
        try:
            cmd_ovpn = ["journalctl", "-u", "openvpn@server", "-n", "20", "--no-pager"]
            cmd_back = ["journalctl", "-u", "vpnmaster-backend", "-n", "20", "--no-pager"]
            
            ovpn_out = subprocess.run(cmd_ovpn, capture_output=True, text=True).stdout
            back_out = subprocess.run(cmd_back, capture_output=True, text=True).stdout
            
            if ovpn_out:
                raw_logs["openvpn"] = ovpn_out.splitlines()
            if back_out:
                raw_logs["backend"] = back_out.splitlines()
                
        except Exception as e:
            logger.error(f"Error fetching raw logs: {e}")

        return {
            "system": system_stats,
            "packages": package_status,
            "services": service_status,
            "recommendations": rec_status,
            "project": {
                "branch": branch,
                "commit": commit,
                "last_message": msg,
                "uncommitted_changes": changes
            },
            "network": network_stats,
            "vpn_security": vpn_security,
            "logs": log_analysis,
            "database": db_health,
            "api_health": api_health,
            "raw_logs": raw_logs,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.critical(f"CRITICAL failure in diagnostics endpoint: {e}")
        # Return a safe fallback so the frontend doesn't crash completely with 500
        return {
            "error": "Internal Server Error during diagnostics",
            "details": str(e),
            "timestamp": time.time()
        }


@router.get("/live-logs")
async def get_live_logs(lines: int = 50):
    """
    Fetch live logs from OpenVPN and Auth script for real-time debugging.
    """
    import shutil
    logs = {
        "openvpn": [],
        "auth": []
    }
    
    # 1. OpenVPN Service Logs (journalctl)
    try:
        # Check if systemd/journalctl is available (Linux)
        if shutil.which("journalctl"):
            cmd = ["journalctl", "-u", "openvpn@server", "-n", str(lines), "--no-pager", "--output", "short-iso"]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode == 0:
                logs["openvpn"] = proc.stdout.splitlines()
            else:
                logs["openvpn"] = [f"Error fetching OpenVPN logs: {proc.stderr}"]
        else:
             # Fallback for dev/mac (tail mostly)
             # In dev we might not have logs, return mock or empty
             logs["openvpn"] = ["Systemd not found. Logs unavailable in dev environment."]
    except Exception as e:
        logs["openvpn"] = [f"Exception fetching OpenVPN logs: {str(e)}"]

    # 2. Auth Script Logs
    auth_log_path = "/var/log/openvpn/auth.log"
    if os.path.exists(auth_log_path):
        try:
            # Use tail to get last N lines
            cmd = ["tail", "-n", str(lines), auth_log_path]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode == 0:
                logs["auth"] = proc.stdout.splitlines()
            else:
                 logs["auth"] = [f"Error reading auth.log: {proc.stderr}"]
        except Exception as e:
            logs["auth"] = [f"Exception reading auth.log: {str(e)}"]
    else:
        logs["auth"] = ["Auth log file not found (No connection attempts yet?)"]

    return logs

@router.post("/restart/{service}")
async def restart_service(
    service: str,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin)
):
    """
    Restart a specific system service with verification and safe backend handling.
    """
    import asyncio

    service_map = {
        "openvpn": "openvpn@server",
        "backend": "vpnmaster-backend",
        "nginx": "nginx",
        "wireguard": "wg-quick@wg0"
    }
    
    if service not in service_map:
        return {"status": "error", "message": "Invalid service name"}
    
    target_service = service_map[service]
    
    # helper to check service status
    def get_service_details(svc_name):
        details = {"pid": "unknown", "active_since": "unknown"}
        try:
            # Get MainPID
            pid_cmd = ["systemctl", "show", "--property=MainPID", "--value", svc_name]
            pid_out = subprocess.run(pid_cmd, capture_output=True, text=True).stdout.strip()
            if pid_out and pid_out != "0":
                details["pid"] = pid_out
            
            # Get ActiveEnterTimestamp
            time_cmd = ["systemctl", "show", "--property=ActiveEnterTimestamp", "--value", svc_name]
            time_out = subprocess.run(time_cmd, capture_output=True, text=True).stdout.strip()
            if time_out:
                details["active_since"] = time_out
        except:
            pass
        return details

    try:
        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
             return {"status": "error", "message": "Systemctl not found (Dev Env?)"}

        # Special handling for Backend Self-Restart
        if service == "backend":
            async def delayed_restart():
                await asyncio.sleep(2) # Give time to return response
                logger.warning("♻️  Restarting Backend Service via delayed task...")
                subprocess.run([systemctl_path, "restart", target_service])

            background_tasks.add_task(delayed_restart)
            return {
                "status": "success", 
                "message": "Backend restart initiated. Service will reboot in 2 seconds.",
                "details": {"action": "delayed_restart"}
            }

        # Standard Restart for other services
        cmd = [systemctl_path, "restart", target_service]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        
        if proc.returncode == 0:
            # Verify new status
            new_details = get_service_details(target_service)
            return {
                "status": "success", 
                "message": f"Service {service} restarted successfully.",
                "details": new_details
            }
        else:
            return {
                "status": "error", 
                "message": f"Failed to restart {service}",
                "debug": proc.stderr.strip() or "Unknown error (exit code non-zero)"
            }
            
    except Exception as e:
        logger.error(f"Restart exception: {e}")
        return {"status": "error", "message": f"Exception restarting {service}: {str(e)}"}
