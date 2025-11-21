#!/usr/bin/env python3
"""
Start a P2P Campus Compute Worker
This machine will contribute its compute resources to the network.
"""

import os
import sys
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(
        description='Run a CampusGrid Worker Node',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python run_worker.py                           # Connect to localhost
  python run_worker.py -m 192.168.1.100          # Connect to specific manager
  python run_worker.py -m 192.168.1.100 -n MyPC  # With custom name
  python run_worker.py -m 192.168.1.100 -u john  # Associate with user
        '''
    )

    parser.add_argument('-m', '--manager',
                        default='localhost',
                        help='Manager server IP/hostname (default: localhost)')

    parser.add_argument('-p', '--port',
                        type=int,
                        default=9999,
                        help='Manager server port (default: 9999)')

    parser.add_argument('-n', '--name',
                        default=None,
                        help='Worker name (default: auto-generated)')

    parser.add_argument('-u', '--user',
                        default='',
                        help='Owner username to earn credits')

    parser.add_argument('--no-docker',
                        action='store_true',
                        help='Disable Docker sandboxing')

    args = parser.parse_args()

    # Set environment variables
    os.environ['MANAGER_HOST'] = args.manager
    os.environ['MANAGER_PORT'] = str(args.port)
    if args.name:
        os.environ['WORKER_NAME'] = args.name
    if args.user:
        os.environ['OWNER_TOKEN'] = args.user
    if args.no_docker:
        os.environ['USE_DOCKER'] = 'false'

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║  ██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗███████╗██████╗      ║
    ║  ██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝██╔════╝██╔══██╗     ║
    ║  ██║ █╗ ██║██║   ██║██████╔╝█████╔╝ █████╗  ██████╔╝     ║
    ║  ██║███╗██║██║   ██║██╔══██╗██╔═██╗ ██╔══╝  ██╔══██╗     ║
    ║  ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗███████╗██║  ██║     ║
    ║   ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝     ║
    ║                                                           ║
    ║         CampusGrid Worker Node                            ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    print(f"[CONFIG] Manager: {args.manager}:{args.port}")
    print(f"[CONFIG] Docker: {'Disabled' if args.no_docker else 'Enabled (if available)'}")
    if args.user:
        print(f"[CONFIG] Owner: {args.user}")
    print()

    # Import and run worker
    from worker.client import WorkerClient, CONFIG

    # Update CONFIG with parsed args
    CONFIG['manager_host'] = args.manager
    CONFIG['manager_port'] = args.port
    if args.name:
        CONFIG['worker_name'] = args.name
    CONFIG['owner_token'] = args.user
    CONFIG['use_docker'] = not args.no_docker

    worker = WorkerClient(CONFIG)
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Worker stopped")
        sys.exit(0)

if __name__ == '__main__':
    main()
