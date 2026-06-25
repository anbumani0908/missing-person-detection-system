"""
Web Dashboard Server for Missing-Person Detector
Provides REST API and WebSocket real-time updates
"""
import os
import csv
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
DASHBOARD_PORT = 5000
MATCHES_DIR = Path("matches")
DB_DIR = Path("database")
LOG_CSV = Path("matches_log.csv")
CONFIG_FILE = Path("config.json")
DETECTION_LOG = Path("detection_log.txt")

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
detection_stats = {
    'total_detections': 0,
    'high_confidence': 0,
    'medium_confidence': 0,
    'low_confidence': 0,
    'unique_people': set(),
    'cameras_active': {},
    'last_detection': None,
    'system_status': 'stopped',
    'uptime_start': None
}

active_alerts = []
recent_detections = []


class FileWatcher(FileSystemEventHandler):
    """Watch for new matches and log updates"""
    
    def __init__(self, socketio_instance):
        self.socketio = socketio_instance
        self.last_log_size = 0
        if LOG_CSV.exists():
            self.last_log_size = LOG_CSV.stat().st_size
    
    def on_created(self, event):
        """Handle new file creation"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # New match image
        if file_path.parent == MATCHES_DIR and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            print(f"New match detected: {file_path.name}")
            self.process_new_match(file_path)
    
    def on_modified(self, event):
        """Handle file modifications"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Log file updated
        if file_path == LOG_CSV:
            self.process_log_update()
    
    def process_new_match(self, image_path: Path):
        """Process newly detected match"""
        # Parse filename: YYYYMMDD_HHMMSS_ID.jpg
        try:
            name_parts = image_path.stem.split('_')
            if len(name_parts) >= 3:
                timestamp_str = f"{name_parts[0]}_{name_parts[1]}"
                person_id = name_parts[2]
                
                # Get latest log entry for this match
                match_data = self.get_latest_log_entry(person_id)
                
                if match_data:
                    alert = {
                        'id': len(active_alerts),
                        'person_id': match_data['id'],
                        'person_name': match_data['name'],
                        'confidence': match_data['confidence'],
                        'score': float(match_data['score']),
                        'timestamp': match_data['timestamp'],
                        'image': f"/api/matches/{image_path.name}",
                        'camera': match_data.get('camera', 'Unknown')
                    }
                    
                    active_alerts.insert(0, alert)
                    if len(active_alerts) > 50:
                        active_alerts.pop()
                    
                    # Emit real-time update
                    self.socketio.emit('new_detection', alert)
                    print(f"Alert emitted: {match_data['name']}")
        
        except Exception as e:
            print(f"Error processing match: {e}")
    
    def process_log_update(self):
        """Process CSV log updates"""
        try:
            current_size = LOG_CSV.stat().st_size
            if current_size > self.last_log_size:
                self.last_log_size = current_size
                update_detection_stats()
                self.socketio.emit('stats_update', get_stats())
        except Exception as e:
            print(f"Error processing log update: {e}")
    
    def get_latest_log_entry(self, person_id: str) -> Optional[Dict]:
        """Get the most recent log entry for a person"""
        if not LOG_CSV.exists():
            return None
        
        try:
            with open(LOG_CSV, 'r') as f:
                reader = csv.DictReader(f)
                matches = [row for row in reader if row['id'] == person_id]
                if matches:
                    return matches[-1]
        except Exception as e:
            print(f"Error reading log: {e}")
        
        return None


def update_detection_stats():
    """Update detection statistics from log file"""
    global detection_stats
    
    if not LOG_CSV.exists():
        return
    
    try:
        with open(LOG_CSV, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            detection_stats['total_detections'] = len(rows)
            detection_stats['high_confidence'] = sum(1 for r in rows if r['confidence'] == 'HIGH')
            detection_stats['medium_confidence'] = sum(1 for r in rows if r['confidence'] == 'MED')
            detection_stats['low_confidence'] = sum(1 for r in rows if r['confidence'] == 'LOW')
            detection_stats['unique_people'] = set(r['id'] for r in rows)
            
            if rows:
                last = rows[-1]
                detection_stats['last_detection'] = {
                    'name': last['name'],
                    'timestamp': last['timestamp'],
                    'confidence': last['confidence']
                }
    
    except Exception as e:
        print(f"Error updating stats: {e}")


def load_database_info() -> List[Dict]:
    """Load information about people in the database"""
    people = []
    
    if not DB_DIR.exists():
        return people
    
    for img_path in sorted(DB_DIR.glob("*")):
        if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
            continue
        
        name_raw = img_path.stem
        if "_" in name_raw:
            person_id, name = name_raw.split("_", 1)
        else:
            person_id = name = name_raw
        
        people.append({
            'id': person_id,
            'name': name.replace('_', ' '),
            'image': f"/api/database/{img_path.name}",
            'added': datetime.fromtimestamp(img_path.stat().st_mtime).isoformat()
        })
    
    return people


def get_detection_history(hours: int = 24) -> List[Dict]:
    """Get detection history for the specified time period"""
    if not LOG_CSV.exists():
        return []
    
    cutoff = datetime.now() - timedelta(hours=hours)
    history = []
    
    try:
        with open(LOG_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    timestamp = datetime.fromisoformat(row['timestamp'])
                    if timestamp >= cutoff:
                        history.append({
                            'id': row['id'],
                            'name': row['name'],
                            'score': float(row['score']),
                            'confidence': row['confidence'],
                            'timestamp': row['timestamp'],
                            'camera': row.get('camera', 'Unknown'),
                            'snapshot': row['snapshot']
                        })
                except Exception as e:
                    print(f"Error parsing row: {e}")
                    continue
    
    except Exception as e:
        print(f"Error reading history: {e}")
    
    return history


def get_stats() -> Dict:
    """Get current statistics"""
    uptime = None
    if detection_stats['uptime_start']:
        uptime = int(time.time() - detection_stats['uptime_start'])
    
    return {
        'total_detections': detection_stats['total_detections'],
        'high_confidence': detection_stats['high_confidence'],
        'medium_confidence': detection_stats['medium_confidence'],
        'low_confidence': detection_stats['low_confidence'],
        'unique_people': len(detection_stats['unique_people']),
        'last_detection': detection_stats['last_detection'],
        'system_status': detection_stats['system_status'],
        'uptime': uptime,
        'cameras_active': detection_stats['cameras_active']
    }


def get_timeline_data(hours: int = 24) -> Dict:
    """Get timeline data for charts"""
    if not LOG_CSV.exists():
        return {'labels': [], 'data': []}
    
    cutoff = datetime.now() - timedelta(hours=hours)
    hourly_counts = defaultdict(int)
    
    try:
        with open(LOG_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    timestamp = datetime.fromisoformat(row['timestamp'])
                    if timestamp >= cutoff:
                        hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                        hourly_counts[hour_key] += 1
                except:
                    continue
    except Exception as e:
        print(f"Error reading timeline: {e}")
    
    # Generate all hours in range
    labels = []
    data = []
    current = cutoff.replace(minute=0, second=0, microsecond=0)
    end = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    while current <= end:
        hour_key = current.strftime('%Y-%m-%d %H:00')
        labels.append(current.strftime('%H:00'))
        data.append(hourly_counts.get(hour_key, 0))
        current += timedelta(hours=1)
    
    return {'labels': labels, 'data': data}


# ==================== API ROUTES ====================

@app.route('/')
def index():
    """Serve the dashboard HTML"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/stats')
def api_stats():
    """Get current statistics"""
    return jsonify(get_stats())

@app.route('/api/alerts')
def api_alerts():
    """Get recent alerts"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify(active_alerts[:limit])

@app.route('/api/database')
def api_database():
    """Get database information"""
    people = load_database_info()
    return jsonify(people)

@app.route('/api/database/<filename>')
def serve_database_image(filename):
    """Serve database images"""
    return send_from_directory(DB_DIR, filename)

@app.route('/api/matches/<filename>')
def serve_match_image(filename):
    """Serve match images"""
    return send_from_directory(MATCHES_DIR, filename)

@app.route('/api/history')
def api_history():
    """Get detection history"""
    hours = request.args.get('hours', 24, type=int)
    history = get_detection_history(hours)
    return jsonify(history)

@app.route('/api/timeline')
def api_timeline():
    """Get timeline data for charts"""
    hours = request.args.get('hours', 24, type=int)
    timeline = get_timeline_data(hours)
    return jsonify(timeline)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    if request.method == 'GET':
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return jsonify(config)
        return jsonify({})
    
    elif request.method == 'POST':
        config = request.json
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        socketio.emit('config_update', config)
        return jsonify({'status': 'success'})

@app.route('/api/system/status')
def api_system_status():
    """Get detailed system status"""
    status = {
        'detection_active': detection_stats['system_status'] == 'running',
        'uptime': get_stats()['uptime'],
        'cameras': detection_stats['cameras_active'],
        'logs': {
            'matches_log_size': LOG_CSV.stat().st_size if LOG_CSV.exists() else 0,
            'total_matches': len(list(MATCHES_DIR.glob("*.jpg"))) if MATCHES_DIR.exists() else 0,
            'database_size': len(list(DB_DIR.glob("*"))) if DB_DIR.exists() else 0
        }
    }
    return jsonify(status)

@app.route('/api/person/<person_id>')
def api_person_detail(person_id):
    """Get detailed information about a specific person"""
    # Get all detections for this person
    detections = []
    
    if LOG_CSV.exists():
        try:
            with open(LOG_CSV, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == person_id:
                        detections.append({
                            'timestamp': row['timestamp'],
                            'score': float(row['score']),
                            'confidence': row['confidence'],
                            'camera': row.get('camera', 'Unknown'),
                            'snapshot': row['snapshot']
                        })
        except Exception as e:
            print(f"Error getting person details: {e}")
    
    # Get person info from database
    person_info = None
    for person in load_database_info():
        if person['id'] == person_id:
            person_info = person
            break
    
    return jsonify({
        'person': person_info,
        'detections': detections,
        'total_detections': len(detections)
    })

@app.route('/api/search')
def api_search():
    """Search detections by name or ID"""
    query = request.args.get('q', '').lower()
    
    if not query or not LOG_CSV.exists():
        return jsonify([])
    
    results = []
    try:
        with open(LOG_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if query in row['name'].lower() or query in row['id'].lower():
                    results.append({
                        'id': row['id'],
                        'name': row['name'],
                        'timestamp': row['timestamp'],
                        'confidence': row['confidence'],
                        'score': float(row['score'])
                    })
    except Exception as e:
        print(f"Search error: {e}")
    
    return jsonify(results[-50:])  # Return last 50 matches


# ==================== WEBSOCKET EVENTS ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'status': 'connected'})
    emit('stats_update', get_stats())

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('request_stats')
def handle_stats_request():
    """Handle stats request"""
    emit('stats_update', get_stats())

@socketio.on('system_command')
def handle_system_command(data):
    """Handle system commands (start/stop detection)"""
    command = data.get('command')
    
    if command == 'start':
        detection_stats['system_status'] = 'running'
        detection_stats['uptime_start'] = time.time()
        emit('system_status', {'status': 'running'}, broadcast=True)
    
    elif command == 'stop':
        detection_stats['system_status'] = 'stopped'
        emit('system_status', {'status': 'stopped'}, broadcast=True)


def background_stats_updater():
    """Background thread to periodically update stats"""
    while True:
        time.sleep(5)  # Update every 5 seconds
        update_detection_stats()
        socketio.emit('stats_update', get_stats())


def start_file_watcher():
    """Start watching for file changes"""
    event_handler = FileWatcher(socketio)
    observer = Observer()
    
    # Watch matches directory
    if MATCHES_DIR.exists():
        observer.schedule(event_handler, str(MATCHES_DIR), recursive=False)
    
    # Watch for log file changes
    observer.schedule(event_handler, ".", recursive=False)
    
    observer.start()
    print("File watcher started")
    return observer


if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Missing-Person Detector - Web Dashboard Server")
    print("=" * 60)
    
    # Create directories if they don't exist
    MATCHES_DIR.mkdir(exist_ok=True)
    DB_DIR.mkdir(exist_ok=True)
    
    # Initial stats update
    update_detection_stats()
    
    # Start file watcher
    observer = start_file_watcher()
    
    # Start background stats updater
    stats_thread = threading.Thread(target=background_stats_updater, daemon=True)
    stats_thread.start()
    
    print(f"\n✓ Server starting on http://localhost:{DASHBOARD_PORT}")
    print(f"✓ WebSocket enabled for real-time updates")
    print(f"✓ File watcher monitoring: {MATCHES_DIR}")
    print(f"\n📊 Dashboard URL: http://localhost:{DASHBOARD_PORT}")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        socketio.run(app, host='0.0.0.0', port=DASHBOARD_PORT, debug=False)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        observer.stop()
        observer.join()
        print("✓ Server stopped")