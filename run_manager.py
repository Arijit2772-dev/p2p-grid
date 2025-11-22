#!/usr/bin/env python3
"""
Start the P2P Campus Compute Manager
This runs both the TCP server (for workers) and the web dashboard.
"""

import os
import sys
import threading
import time
import socket

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Create a socket to determine the outbound IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def run_tcp_server():
    """Run the TCP server for worker connections"""
    from manager.server import start_server
    start_server()

def start_dashboard():
    """Run the web dashboard"""
    from manager.dashboard import run_dashboard
    run_dashboard(debug=False)

def main():
    local_ip = get_local_ip()

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
    ║         P2P Campus Compute Sharing Network                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    print("[STARTUP] Initializing CampusGrid Manager...")
    print()
    print("=" * 60)
    print(f"  YOUR NETWORK IP: {local_ip}")
    print("=" * 60)
    print()
    print("  DASHBOARD (Web UI):")
    print(f"    Local:   http://localhost:5001")
    print(f"    Network: http://{local_ip}:5001")
    print()
    print("  WORKER CONNECTION:")
    print(f"    Port: 9999")
    print()
    print("  TO CONNECT WORKERS FROM OTHER LAPTOPS:")
    print(f"    python3 run_worker.py -m {local_ip} -n \"WorkerName\" -u <username>")
    print()
    print("=" * 60)
    print()

    # Start TCP server in background thread
    tcp_thread = threading.Thread(target=run_tcp_server, daemon=True)
    tcp_thread.start()

    # Give TCP server time to start
    time.sleep(1)

    # Run dashboard in main thread
    try:
        start_dashboard()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping CampusGrid Manager...")
        sys.exit(0)

if __name__ == '__main__':
    main()
