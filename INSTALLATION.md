# Professional Dashboard Enhancement - Installation Guide

## 📦 Required Dependencies

Add these to `package.json`:

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "recharts": "^2.10.3",
    "lucide-react": "^0.294.0",
    "axios": "^1.6.2",
    "qrcode.react": "^3.1.0",
    "react-simple-maps": "^3.0.0",
    "react-calendar-heatmap": "^1.9.0",
    "d3-scale": "^4.0.2"
  }
}
```

## 🚀 Installation Steps

### Option 1: Manual Installation (Recommended)

```bash
cd /Users/majlotfi/.gemini/antigravity/playground/radiant-kuiper/vpn-master-panel-lite/frontend

# Install new dependencies
npm install qrcode.react@^3.1.0
npm install react-simple-maps@^3.0.0
npm install react-calendar-heatmap@^1.9.0
npm install d3-scale@^4.0.2

# Build
npm run build
```

### Option 2: Server Deployment

The `update.sh` script will handle installation automatically:

```bash
# On server
cd ~/vpn-master-panel-lite
sudo ./update.sh
```

## 📝 Files to Push

Make sure these files are committed:

### Frontend
- `frontend/src/components/ErrorBoundary.jsx`
- `frontend/src/components/Skeletons.jsx`
- `frontend/src/components/States.jsx`
- `frontend/src/components/RefreshIndicator.jsx`
- `frontend/src/components/QRCodeModal.jsx`
- `frontend/src/components/ProtocolDistributionChart.jsx`
- `frontend/src/components/NotificationCenter.jsx`
- `frontend/src/components/ActivityTimeline.jsx`
- `frontend/src/components/DashboardEnhanced.jsx`
- `frontend/src/App.jsx` (updated with ErrorBoundary)

### Backend
- `backend/app/api/notifications.py`
- `backend/app/api/activity.py`
- `backend/app/api/monitoring.py` (updated)
- `backend/app/main.py` (updated)

## ✅ Verification

After deployment, verify:

1. Dashboard loads without errors
2. All new components render
3. API endpoints respond:
   - `/api/v1/monitoring/protocol-distribution`
   - `/api/v1/notifications`
   - `/api/v1/activity/recent`

## 🔧 Troubleshooting

### Issue: Dependencies not installing
**Solution**: Run `npm install` manually in frontend directory

### Issue: Components not found
**Solution**: Verify all files are pushed to repository

### Issue: API endpoints 404
**Solution**: Restart backend service after deployment
