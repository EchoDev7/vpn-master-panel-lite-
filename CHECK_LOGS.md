# Debug Commands

Run these on the server to check logs:

```bash
# Check backend logs (last 100 lines)
journalctl -u vpn-backend -n 100 --no-pager

# Check backend logs (live)
journalctl -u vpn-backend -f

# Check if backend is running
systemctl status vpn-backend

# Check backend errors only
journalctl -u vpn-backend -p err -n 50
```

Send me the output!
