import os
import subprocess
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class SSLService:
    def __init__(self):
        self.nginx_conf_dir = "/etc/nginx/sites-available"
        self.certbot_path = "/usr/bin/certbot"
        
    def _run_cmd(self, cmd: str) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd, shell=True, check=True, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd}\nError: {e.stderr}")
            return False, e.stderr

    def stream_letsencrypt_cert(self, domain: str, email: str):
        """
        Generator that yields live Certbot logs for streaming to the frontend.
        """
        if not domain or not email:
            yield "ERROR: Domain and email are required.\n"
            return
            
        yield f"INFO: Initializing Let's Encrypt SSL Request for {domain}...\n"
        
        certbot_path = self.certbot_path
        if not os.path.exists(certbot_path):
             certbot_path = "certbot"
             
        cmd = f"{certbot_path} certonly --non-interactive --agree-tos -m {email} -d {domain} --nginx"
        yield f"EXEC: Running Nginx plugin verification...\n"
        
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ""):
            yield f"CERTBOT: {line}"
        process.stdout.close()
        process.wait()
        
        if process.returncode == 0:
             yield f"\nSUCCESS: SSL Certificate successfully issued for {domain}!\n"
             yield "EXEC: Reloading Nginx to apply new certificates...\n"
             subprocess.run("systemctl reload nginx", shell=True)
             yield "DONE: Nginx reloaded. Panel is now secured.\n"
             return
             
        yield f"\nWARN: Nginx plugin failed (Exit Code: {process.returncode}).\n"
        yield "INFO: Attempting aggressive Standalone fallback mode...\n"
        yield "EXEC: Stopping Nginx service temporarily on port 80...\n"
        subprocess.run("systemctl stop nginx", shell=True)
        
        cmd_fallback = f"{certbot_path} certonly --standalone --non-interactive --agree-tos -m {email} -d {domain}"
        yield f"EXEC: Running Standalone plugin verification...\n"
        
        process2 = subprocess.Popen(cmd_fallback, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process2.stdout.readline, ""):
            yield f"CERTBOT: {line}"
        process2.stdout.close()
        process2.wait()
        
        yield "EXEC: Starting Nginx service back up...\n"
        subprocess.run("systemctl start nginx", shell=True)
        
        if process2.returncode == 0:
             yield f"\nSUCCESS: SSL Certificate successfully issued for {domain} via Standalone mode!\n"
             yield "DONE: Web server restored. Panel is now secured.\n"
        else:
             yield f"\nERROR: Certbot standalone request failed (Exit Code: {process2.returncode}).\n"
             yield "FATAL: Please check your domain DNS records and ensure Port 80 is strictly open.\n"
