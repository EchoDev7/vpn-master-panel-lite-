from fastapi import APIRouter, Depends
from typing import Dict, Any, List
import subprocess
import shutil
import logging
import os
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
    Get comprehensive system diagnostics, including:
    - System Resources (CPU/RAM/Disk)
    - Network Status (Public IP, Ports)
    - Service Status (Systemd)
    - Package Versions (Installed vs Latest)
    - Recommended Tools
    - Project Info
    """
    import psutil
    import time
    
    # 1. System Resources
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        try:
            load = psutil.getloadavg()
        except AttributeError:
            load = (0, 0, 0)
        
        system_stats = {
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
            "load_avg": [0, 0, 0],
            "memory": {"used_mb": 0, "total_mb": 0, "percent": 0},
            "disk": {"used_gb": 0, "total_gb": 0, "percent": 0}
        }
    
    # 2. Package Versions
    package_status = []
    try:
        packages = ["openvpn", "nginx", "python3", "pip", "node", "npm", "git", "curl", "ufw", "wg", "sqlite3"]
        
        for pkg in packages:
            try:
                # Use apt-cache for system packages
                if pkg in ["openvpn", "nginx", "git", "curl", "ufw", "sqlite3"]:
                    versions = get_package_version(pkg)
                    package_status.append({
                        "name": pkg,
                        "installed": versions["installed"],
                        "latest": versions["latest"],
                        "status": "Update Available" if versions["installed"] != versions["latest"] and versions["installed"] != "Not Installed" else "Up to date"
                    })
                elif pkg == "python3":
                     # Python is special, usually python3 package
                     versions = get_package_version("python3")
                     cmd_ver = get_command_version("python3")
                     package_status.append({
                         "name": "python3",
                         "installed": cmd_ver, # Show actual running version
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
                     # Check nodejs package for apt
                     versions = get_package_version("nodejs")
                     cmd_ver = get_command_version("node", "-v")
                     package_status.append({
                         "name": "node",
                         "installed": cmd_ver,
                         "latest": versions["latest"], # Might be different depending on repo
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
    service_status = []
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
    rec_status = []
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

    # 6. Network & Connectivity (Enhanced)
    try:
        # Public IPs
        public_ipv4 = subprocess.run(["curl", "-4", "-s", "--max-time", "2", "ifconfig.me"], capture_output=True, text=True).stdout.strip() or "Unknown"
        public_ipv6 = subprocess.run(["curl", "-6", "-s", "--max-time", "2", "-H", "User-Agent: curl", "ipv6.icanhazip.com"], capture_output=True, text=True).stdout.strip() or "Not Detected"
        
        # Latency
        try:
            latency_out = subprocess.run(["ping", "-c", "1", "8.8.8.8"], capture_output=True, text=True).stdout
            latency = latency_out.split("time=")[1].split(" ")[0] + "ms"
        except:
            latency = "Timeout"
            
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
                        port = addr.split(":")[-1]
                        if port in ["8000", "3000", "1194", "51820", "443", "80", "22"]:
                             listening_ports.append(f"{addr}")
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
    vpn_security = {}
    try:
        # TUN
        tun_status = os.path.exists("/dev/net/tun")
        
        # IP Forwarding
        try:
            with open("/proc/sys/net/ipv4/ip_forward", "r") as f:
                ip_fwd = f.read().strip() == "1"
        except:
            ip_fwd = False
            
        # Cert Expiry
        cert_expiry = "Unknown"
        if os.path.exists("/etc/openvpn/server.crt"):
            try:
                cert_out = subprocess.run(["openssl", "x509", "-enddate", "-noout", "-in", "/etc/openvpn/server.crt"], capture_output=True, text=True).stdout
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
    log_analysis = []
    try:
        log_files = ["/var/log/syslog", "/var/log/openvpn/openvpn.log", "/var/log/nginx/error.log"]
        error_patterns = {
            "private key password verification failed": {"level": "CRITICAL", "msg": "PKI Key Encrypted/Corrupt", "fix": "Run './update.sh' to force-regenerate keys."},
            "Address already in use": {"level": "CRITICAL", "msg": "Port Conflict", "fix": "Check if another service is using the port (netstat -tulnp)."},
            "Options error": {"level": "ERROR", "msg": "Configuration Syntax Error", "fix": "Check server.conf for invalid directives."},
            "Permission denied": {"level": "ERROR", "msg": "File Permission Issue", "fix": "Run 'chown -R root:root /etc/openvpn' or check AppArmor."},
            "CRL: cannot read": {"level": "WARN", "msg": "CRL File Missing/Unreadable", "fix": "Regenerate CRL or check permissions."}
        }
        
        # We can't read root logs easily if not running as root, 
        # but the service runs as root, so it should work.
        # Reading last 50 lines of journalctl for services is safer
        
        cmd_ovpn = ["journalctl", "-u", "openvpn@server", "-n", "50", "--no-pager"]
        cmd_back = ["journalctl", "-u", "vpnmaster-backend", "-n", "50", "--no-pager"]
        
        logs_to_scan = ""
        logs_to_scan += subprocess.run(cmd_ovpn, capture_output=True, text=True).stdout
        logs_to_scan += subprocess.run(cmd_back, capture_output=True, text=True).stdout
        
        for line in logs_to_scan.splitlines():
            for pattern, info in error_patterns.items():
                if pattern in line:
                    # Avoid duplicates
                    issue = {
                        "level": info["level"],
                        "message": info["msg"],
                        "fix": info["fix"],
                        "log_snippet": line[:100] + "..."
                    }
                    if issue not in log_analysis:
                        log_analysis.append(issue)
                        
        if not log_analysis:
             log_analysis = [{"level": "OK", "message": "No critical error patterns detected.", "fix": ""}]
             
    except Exception as e:
        logger.error(f"Error in log analysis: {e}")
        log_analysis = [{"level": "ERROR", "message": f"Failed to analyze logs: {str(e)}", "fix": ""}]

    # 9. Deep Database Check
    db_health = {"status": "Unknown", "details": []}
    try:
        from ..database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # Integrity
            res = db.execute(text("PRAGMA integrity_check")).fetchone()[0]
            db_health["integrity"] = "OK" if res == "ok" else "FAIL"
            
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
        "timestamp": time.time()
    }
