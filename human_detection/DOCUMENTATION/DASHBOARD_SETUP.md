# Web Dashboard Setup Guide

## 🎯 Overview

The web dashboard provides a modern, real-time interface for monitoring your missing-person detection system. It features:

- 📊 **Real-time statistics** - Live updates via WebSocket
- 🚨 **Alert feed** - Instant notifications of detections
- 📈 **Timeline charts** - Visual detection history
- 👥 **Database viewer** - See all monitored individuals
- 🎨 **Modern UI** - Sleek, dark-themed dashboard

---

## 📦 Installation

### Step 1: Install Dependencies

```bash
# Install dashboard requirements
pip install -r requirements_dashboard.txt
```

This installs:
- Flask (web server)
- Flask-CORS (cross-origin support)
- Flask-SocketIO (real-time updates)
- Watchdog (file monitoring)
- Requests (HTTP client)

### Step 2: Verify Installation

```bash
python -c "import flask, flask_socketio, watchdog; print('✓ All dependencies installed')"
```

---

## 🚀 Quick Start

### Option 1: Dashboard Only (View Existing Data)

```bash
# Start the dashboard server
python dashboard_server.py
```

Then open your browser to: **http://localhost:5000**

### Option 2: Dashboard + Detection System

**Terminal 1 - Start Dashboard:**
```bash
python dashboard_server.py
```

**Terminal 2 - Start Detector:**
```bash
python missing_person_detector_improved.py
```

---

## 📁 File Structure

```
project/
├── dashboard_server.py          # Backend server with API
├── dashboard.html               # Frontend interface
├── dashboard_integration.py     # Integration module (optional)
├── requirements_dashboard.txt   # Dashboard dependencies
├── missing_person_detector_improved.py  # Main detector
├── config.json                  # Configuration
├── database/                    # Person images
├── matches/                     # Detection snapshots
├── matches_log.csv             # Detection log
└── detection_log.txt           # Detailed logs
```

---

## 🌐 Dashboard Features

### 1. Header Section
- **System Status Badge** - Shows if detection is running
- **Real-time Connection Indicator** - WebSocket status

### 2. Statistics Cards
- **Total Detections** - All-time match count
- **High Confidence** - Critical alerts (>60% confidence)
- **Unique People** - Number of different individuals detected
- **System Uptime** - How long the system has been running

### 3. Recent Alerts Panel
- **Live feed** of detections
- **Images** of detected faces
- **Confidence levels** with color coding:
  - 🔴 Red = High confidence (≥60%)
  - 🟠 Orange = Medium confidence (≥50%)
  - 🟡 Yellow = Low confidence (≥40%)
- **Timestamps** and camera sources

### 4. Detection Timeline Chart
- **Visual graph** of detections over time
- **Adjustable timeframes**: 6, 12, 24, or 48 hours
- **Interactive** - hover for details

### 5. Watchlist Database
- **Grid view** of all monitored people
- **Profile images** with names and IDs
- **Live count** of database size

---

## 🔧 API Endpoints

The dashboard server exposes these REST API endpoints:

### GET /api/stats
Returns current statistics
```json
{
  "total_detections": 42,
  "high_confidence": 15,
  "unique_people": 8,
  "system_status": "running",
  "uptime": 3600
}
```

### GET /api/alerts?limit=20
Returns recent alerts

### GET /api/database
Returns all people in database

### GET /api/history?hours=24
Returns detection history for specified hours

### GET /api/timeline?hours=24
Returns timeline data for charts

### GET /api/config
Returns current configuration

### POST /api/config
Updates configuration

### GET /api/person/{person_id}
Returns detailed info about a specific person

### GET /api/search?q=query
Searches detections by name or ID

---

## 🔌 WebSocket Events

Real-time updates via Socket.IO:

### Server → Client Events:
- `connected` - Connection established
- `stats_update` - Statistics updated
- `new_detection` - New person detected
- `config_update` - Configuration changed
- `system_status` - System status changed

### Client → Server Events:
- `request_stats` - Request statistics update
- `system_command` - Send system command (start/stop)

---

## 🎨 Customization

### Change Dashboard Port

Edit `dashboard_server.py`:
```python
DASHBOARD_PORT = 8080  # Change from 5000
```

### Modify Update Interval

Edit `dashboard_server.py`:
```python
def background_stats_updater():
    while True:
        time.sleep(10)  # Change from 5 seconds to 10
        # ...
```

### Change Dashboard Theme

Edit `dashboard.html` CSS variables:
```css
:root {
    --bg-primary: #0a0e27;      /* Main background */
    --accent-blue: #4da3ff;     /* Primary accent */
    --accent-red: #ff3366;      /* Alert color */
    /* ... customize colors ... */
}
```

---

## 🔍 Troubleshooting

### Issue: "Address already in use"
**Solution:** Another process is using port 5000
```bash
# Find and kill the process
lsof -ti:5000 | xargs kill -9

# Or change the port in dashboard_server.py
```

### Issue: Dashboard shows "Disconnected"
**Causes:**
1. Dashboard server not running
2. Firewall blocking port 5000
3. Wrong URL in dashboard.html

**Solution:**
```bash
# Check if server is running
curl http://localhost:5000/api/stats

# Update URL in dashboard.html if needed
const socket = io('http://YOUR_IP:5000');
```

### Issue: No alerts appearing
**Causes:**
1. No detections happening
2. File watcher not working
3. matches/ directory permissions

**Solution:**
```bash
# Check if matches are being saved
ls -la matches/

# Check matches_log.csv
cat matches_log.csv

# Restart dashboard server
```

### Issue: Images not loading
**Causes:**
1. Incorrect file paths
2. CORS issues
3. Missing image files

**Solution:**
```bash
# Verify image paths
ls database/
ls matches/

# Check browser console for errors (F12)
```

---

## 📱 Remote Access

### Access Dashboard from Other Devices

1. **Find your IP address:**
   ```bash
   # Linux/Mac
   ifconfig | grep "inet "
   
   # Windows
   ipconfig
   ```

2. **Update dashboard.html:**
   ```javascript
   // Change from localhost to your IP
   const socket = io('http://192.168.1.100:5000');
   ```

3. **Access from any device on your network:**
   ```
   http://192.168.1.100:5000
   ```

### Enable External Access (Advanced)

⚠️ **Security Warning:** Only do this on trusted networks

```bash
# The server already binds to 0.0.0.0
# Just configure your firewall/router

# Ubuntu firewall
sudo ufw allow 5000/tcp

# Forward port in router settings if accessing from internet
```

---

## 🔐 Security Considerations

### Current Setup
- No authentication (local network only)
- No HTTPS/SSL
- Open CORS policy

### For Production Use

1. **Add Authentication:**
   ```python
   # In dashboard_server.py
   from flask_httpauth import HTTPBasicAuth
   
   auth = HTTPBasicAuth()
   
   @auth.verify_password
   def verify_password(username, password):
       # Implement authentication
       pass
   ```

2. **Enable HTTPS:**
   ```python
   # Use SSL certificates
   socketio.run(app, 
       ssl_context=('cert.pem', 'key.pem'),
       # ...
   )
   ```

3. **Restrict CORS:**
   ```python
   # In dashboard_server.py
   CORS(app, origins=['http://yourdomain.com'])
   ```

---

## 🚀 Performance Tips

### For Large Deployments

1. **Limit Alert History:**
   Edit `dashboard_server.py`:
   ```python
   @app.route('/api/alerts')
   def api_alerts():
       limit = min(request.args.get('limit', 20, type=int), 100)
       # Prevent loading too many alerts
   ```

2. **Database Optimization:**
   ```python
   # Cache database info
   from functools import lru_cache
   
   @lru_cache(maxsize=1)
   def load_database_info():
       # ...
   ```

3. **Reduce Update Frequency:**
   ```javascript
   // In dashboard.html
   setInterval(() => {
       loadStats();
   }, 60000);  // Change from 30s to 60s
   ```

---

## 📊 Data Export

### Export Detection History

```python
# Create export script
import csv
import json

# Export to JSON
with open('matches_log.csv', 'r') as f:
    reader = csv.DictReader(f)
    data = list(reader)

with open('export.json', 'w') as f:
    json.dump(data, f, indent=2)
```

### Generate Reports

```python
# Create reporting script
from datetime import datetime, timedelta
import pandas as pd

# Load data
df = pd.read_csv('matches_log.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter last 24 hours
recent = df[df['timestamp'] > datetime.now() - timedelta(hours=24)]

# Generate report
print(f"Total detections: {len(recent)}")
print(f"Unique people: {recent['id'].nunique()}")
print(f"High confidence: {len(recent[recent['confidence'] == 'HIGH'])}")
```

---

## 🔄 Updates & Maintenance

### Updating the Dashboard

```bash
# Pull latest changes
git pull

# Update dependencies
pip install -r requirements_dashboard.txt --upgrade

# Restart server
# Ctrl+C to stop
python dashboard_server.py
```

### Backup Data

```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
mkdir -p backups/$DATE

cp matches_log.csv backups/$DATE/
cp config.json backups/$DATE/
cp -r database backups/$DATE/
cp -r matches backups/$DATE/

echo "Backup created: backups/$DATE"
```

---

## 💡 Advanced Usage

### Integration with Detection System

Add to `missing_person_detector_improved.py`:

```python
from dashboard_integration import DashboardIntegration

# In main() function
dashboard = DashboardIntegration()
dashboard.update_system_status('running')

# When detection occurs
dashboard.notify_detection(
    person_id=entry['id'],
    person_name=entry['name'],
    confidence=confidence,
    score=best_sim,
    image_path=str(path)
)

# On shutdown
dashboard.update_system_status('stopped')
```

### Custom Alerts

Edit `dashboard.html`:

```javascript
// Play custom sound
function playAlertSound() {
    const audio = new Audio('alert.mp3');
    audio.play();
}

// Send email notification (requires backend)
function sendEmailAlert(detection) {
    fetch('/api/send-email', {
        method: 'POST',
        body: JSON.stringify(detection)
    });
}
```

---

## 📞 Support & Troubleshooting

### Check Logs

```bash
# Dashboard server logs
# (shown in terminal where dashboard_server.py is running)

# Detection system logs
tail -f detection_log.txt

# Browser console
# Open browser DevTools (F12) → Console tab
```

### Common Commands

```bash
# Check if dashboard is running
curl http://localhost:5000/api/stats

# Test WebSocket connection
# (Use browser console)
const socket = io('http://localhost:5000');
socket.on('connect', () => console.log('Connected!'));

# View recent detections
curl http://localhost:5000/api/history?hours=1

# Check database
curl http://localhost:5000/api/database
```

---

## 🎓 Next Steps

1. ✅ Set up the dashboard following this guide
2. ✅ Test with sample data
3. ✅ Configure alerts and notifications
4. ✅ Customize the UI to your needs
5. ✅ Set up automated backups
6. ✅ Consider authentication for remote access

---

## 📝 License

This dashboard system is provided as-is for use with the Missing-Person Detector project.

---

**Last Updated:** February 2026  
**Dashboard Version:** 1.0