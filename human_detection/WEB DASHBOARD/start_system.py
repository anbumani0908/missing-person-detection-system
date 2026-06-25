#!/usr/bin/env python3
"""
Quick Start Launcher for Missing-Person Detector + Dashboard
Launches both the detection system and web dashboard in one command
"""
import os
import sys
import subprocess
import time
import signal
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    required = [
        ('flask', 'Flask web framework'),
        ('flask_socketio', 'Flask-SocketIO'),
        ('watchdog', 'File monitoring'),
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
    ]
    
    missing = []
    for module, name in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(name)
    
    if missing:
        print("❌ Missing dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\nInstall with:")
        print("  pip install -r requirements_dashboard.txt")
        return False
    
    return True

def check_files():
    """Check if required files exist"""
    required_files = [
        'dashboard_server.py',
        'dashboard.html',
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print("❌ Missing required files:")
        for file in missing:
            print(f"   - {file}")
        return False
    
    return True

def create_directories():
    """Create required directories"""
    dirs = ['database', 'matches']
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    print("✓ Directories ready")

def start_dashboard():
    """Start the dashboard server"""
    print("\n🌐 Starting dashboard server...")
    process = subprocess.Popen(
        [sys.executable, 'dashboard_server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(2)
    
    if process.poll() is None:
        print("✓ Dashboard server started (PID: {})".format(process.pid))
        print("  URL: http://localhost:5000")
        return process
    else:
        print("❌ Dashboard server failed to start")
        stdout, stderr = process.communicate()
        print("Error:", stderr)
        return None

def start_detector():
    """Start the detection system (optional)"""
    detector_script = None
    
    # Look for detector script
    candidates = [
        'missing_person_detector_improved.py',
        'missing_person_detector.py'
    ]
    
    for candidate in candidates:
        if Path(candidate).exists():
            detector_script = candidate
            break
    
    if not detector_script:
        print("\n⚠ Detector script not found. Dashboard will run without live detection.")
        print("  Available modes:")
        print("  1. View historical data from logs")
        print("  2. Start detector manually later")
        return None
    
    response = input(f"\n🎥 Start detector ({detector_script})? [y/N]: ").strip().lower()
    
    if response == 'y':
        print(f"\n🎥 Starting detector: {detector_script}...")
        process = subprocess.Popen(
            [sys.executable, detector_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            print(f"✓ Detector started (PID: {process.pid})")
            return process
        else:
            print("❌ Detector failed to start")
            stdout, stderr = process.communicate()
            print("Error:", stderr)
            return None
    
    return None

def main():
    """Main launcher"""
    print("=" * 60)
    print("🚀 Missing-Person Detector + Dashboard Launcher")
    print("=" * 60)
    
    # Check dependencies
    print("\n📦 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("✓ All dependencies installed")
    
    # Check files
    print("\n📁 Checking files...")
    if not check_files():
        sys.exit(1)
    print("✓ All required files present")
    
    # Create directories
    print("\n📂 Preparing directories...")
    create_directories()
    
    # Start dashboard
    dashboard_process = start_dashboard()
    if not dashboard_process:
        print("\n❌ Failed to start dashboard server")
        sys.exit(1)
    
    # Start detector (optional)
    detector_process = start_detector()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ SYSTEM READY")
    print("=" * 60)
    print(f"\n📊 Dashboard: http://localhost:5000")
    print(f"🎥 Detection: {'Running' if detector_process else 'Not started'}")
    print("\nPress Ctrl+C to stop all services\n")
    
    # Handle shutdown
    processes = [p for p in [dashboard_process, detector_process] if p]
    
    def signal_handler(sig, frame):
        print("\n\n🛑 Shutting down...")
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        print("✓ All services stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep running
    try:
        # Monitor processes
        while True:
            time.sleep(1)
            
            # Check if dashboard crashed
            if dashboard_process.poll() is not None:
                print("❌ Dashboard server stopped unexpectedly")
                if detector_process:
                    detector_process.terminate()
                break
            
            # Check if detector crashed
            if detector_process and detector_process.poll() is not None:
                print("⚠ Detector stopped")
                detector_process = None
    
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()