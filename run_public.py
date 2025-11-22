#!/usr/bin/env python3
"""
Run CampusGrid with public internet access via ngrok tunnels.
This allows anyone from anywhere to connect as a worker or access the dashboard.

Requirements:
1. Install ngrok: brew install ngrok (Mac) or download from https://ngrok.com/download
2. Sign up at https://ngrok.com and get your authtoken
3. Run: ngrok config add-authtoken YOUR_AUTH_TOKEN
"""

import os
import sys
import subprocess
import time
import threading
import json
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DASHBOARD_PORT = 5001
WORKER_PORT = 9999

def check_ngrok_installed():
    """Check if ngrok is installed"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def start_ngrok_tunnel(port, protocol='http'):
    """Start an ngrok tunnel and return the process"""
    cmd = ['ngrok', protocol, str(port), '--log', 'stdout', '--log-format', 'json']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def get_ngrok_urls():
    """Get public URLs from ngrok API"""
    try:
        import urllib.request
        time.sleep(3)  # Wait for tunnels to establish
        with urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels') as response:
            data = json.loads(response.read().decode())
            urls = {}
            for tunnel in data.get('tunnels', []):
                if 'http' in tunnel.get('proto', ''):
                    urls['dashboard'] = tunnel.get('public_url', '')
                elif 'tcp' in tunnel.get('proto', ''):
                    urls['worker'] = tunnel.get('public_url', '')
            return urls
    except Exception as e:
        return {}

def parse_tcp_url(url):
    """Parse tcp://host:port into (host, port)"""
    # Format: tcp://X.tcp.ngrok.io:PORT
    match = re.match(r'tcp://([^:]+):(\d+)', url)
    if match:
        return match.group(1), match.group(2)
    return None, None

def run_manager():
    """Run the manager server"""
    from manager.server import start_server
    start_server()

def run_dashboard():
    """Run the web dashboard"""
    from manager.dashboard import run_dashboard
    run_dashboard(debug=False)

def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ██████╗ █████╗ ███╗   ███╗██████╗ ██╗   ██╗███████╗   ║
    ║  ██╔════╝██╔══██╗████╗ ████║██╔══██╗██║   ██║██╔════╝   ║
    ║  ██║     ███████║██╔████╔██║██████╔╝██║   ██║███████╗   ║
    ║  ██║     ██╔══██║██║╚██╔╝██║██╔═══╝ ██║   ██║╚════██║   ║
    ║  ╚██████╗██║  ██║██║ ╚═╝ ██║██║     ╚██████╔╝███████║   ║
    ║   ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝      ╚═════╝ ╚══════╝   ║
    ║                                                           ║
    ║         P2P Campus Compute - PUBLIC MODE                  ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Check ngrok
    if not check_ngrok_installed():
        print("[ERROR] ngrok is not installed!")
        print()
        print("Install ngrok:")
        print("  Mac:     brew install ngrok")
        print("  Windows: Download from https://ngrok.com/download")
        print("  Linux:   snap install ngrok")
        print()
        print("Then authenticate:")
        print("  1. Sign up at https://ngrok.com")
        print("  2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken")
        print("  3. Run: ngrok config add-authtoken YOUR_TOKEN")
        sys.exit(1)

    print("[STARTUP] Starting public tunnels...")
    print()

    # Start ngrok tunnels
    # Note: Free ngrok only allows 1 tunnel at a time
    # For both tunnels, you need ngrok paid OR run them separately

    print("[INFO] Starting HTTP tunnel for Dashboard (port 5001)...")
    dashboard_proc = start_ngrok_tunnel(DASHBOARD_PORT, 'http')

    time.sleep(2)

    # Get tunnel URLs
    urls = get_ngrok_urls()

    dashboard_url = urls.get('dashboard', 'Check http://127.0.0.1:4040')

    print()
    print("=" * 65)
    print("  PUBLIC ACCESS ENABLED")
    print("=" * 65)
    print()
    print(f"  DASHBOARD (Share this link!):")
    print(f"    {dashboard_url}")
    print()
    print("  LOCAL ACCESS:")
    print(f"    http://localhost:5001")
    print()
    print("  NGROK INSPECTOR:")
    print("    http://127.0.0.1:4040")
    print()
    print("=" * 65)
    print()
    print("  FOR WORKERS TO CONNECT REMOTELY:")
    print("  Workers still need to be on same network OR use a TCP tunnel.")
    print()
    print("  To expose worker port (9999) for remote workers:")
    print("  Open a NEW terminal and run:")
    print("    ngrok tcp 9999")
    print()
    print("  Then workers can connect using the tcp://X.tcp.ngrok.io:PORT URL")
    print("=" * 65)
    print()

    # Start TCP server in background thread
    tcp_thread = threading.Thread(target=run_manager, daemon=True)
    tcp_thread.start()

    time.sleep(1)

    # Run dashboard in main thread
    try:
        run_dashboard()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping CampusGrid...")
        dashboard_proc.terminate()
        sys.exit(0)

if __name__ == '__main__':
    main()
