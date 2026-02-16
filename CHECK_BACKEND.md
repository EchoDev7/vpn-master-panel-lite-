# Backend Status Check Commands

Run these commands on the server:

```bash
# Check if backend service exists
systemctl status vpn-backend

# Check if backend is running (alternative)
ps aux | grep uvicorn

# Check backend manually
cd /opt/vpn-master-panel/backend
source venv/bin/activate
python -c "from app.main import app; print('Import successful')"

# Try to start backend manually
cd /opt/vpn-master-panel/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Send me the output!
