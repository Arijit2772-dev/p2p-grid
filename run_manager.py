#!/usr/bin/env python3
"""
Start the P2P Campus Compute Manager
This runs both the TCP server (for workers) and the web dashboard.
"""

import os
import sys
import threading
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_tcp_server():
    """Run the TCP server for worker connections"""
    from manager.server import start_server
    start_server()

def start_dashboard():
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
    ║         P2P Campus Compute Sharing Network                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    print("[STARTUP] Initializing CampusGrid Manager...")
    print("[STARTUP] Dashboard will be available at: http://localhost:5001")
    print("[STARTUP] Worker connections accepted on port: 9999")
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
