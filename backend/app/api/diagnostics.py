from fastapi import APIRouter, Depends
from typing import Dict, Any, List
import subprocess
import shutil
import logging
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
    """
    import psutil
    import time
    
    # 1. System Resources
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    load = psutil.getloadavg()
    
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
    
    # 2. Package Versions
    packages = ["openvpn", "nginx", "python3", "pip", "node", "npm", "git", "curl", "ufw", "wg", "sqlite3"]
    package_status = []
    
    for pkg in packages:
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

    # 3. Service Status
    services = ["vpnmaster-backend", "nginx", "openvpn@server", "wg-quick@wg0", "ufw"]
    service_status = []
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

    # 4. Recommended Tools
    recommendations = [
        {"name": "htop", "desc": "Interactive process viewer", "cmd": "htop"},
        {"name": "iftop", "desc": "Network bandwith monitor (interface level)", "cmd": "iftop"},
        {"name": "fail2ban", "desc": "Intrusion prevention framework", "cmd": "fail2ban-client"},
        {"name": "jq", "desc": "Command-line JSON processor", "cmd": "jq"},
        {"name": "speedtest-cli", "desc": "Internet speed measurement", "cmd": "speedtest"},
        {"name": "tree", "desc": "Recursive directory listing", "cmd": "tree"},
    ]
    
    rec_status = []
    for tool in recommendations:
        installed = shutil.which(tool["cmd"]) is not None
        rec_status.append({
            "name": tool["name"],
            "description": tool["desc"],
            "installed": installed
        })

    # 5. Project Info
    try:
         branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
         commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
         msg = subprocess.run(["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True).stdout.strip()
         changes = len(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip().split('\n'))
         if changes == 1 and subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip() == "":
             changes = 0 # Empty string split results in ['']
    except:
         branch, commit, msg, changes = "Unknown", "Unknown", "Unknown", 0

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
        "timestamp": time.time()
    }
