# Contributing

Thanks for contributing to **VPN Master Panel Lite (OpenVPN-only)**.

## Development Setup (Local)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Pull Request Guidelines

- Keep PRs focused (one logical change)
- Avoid unrelated formatting-only changes
- Update docs when behavior changes (README/TROUBLESHOOTING/CHANGELOG)
- Ensure **OpenVPN-only** scope remains intact (no Docker, no WireGuard)

## Reporting Bugs

Please include:
- OS + version (Ubuntu 22.04 is the main target)
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs:
  - `journalctl -u vpnmaster-backend -n 200 --no-pager`
  - `sudo ./check_status.sh`
