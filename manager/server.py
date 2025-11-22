"""
P2P Campus Compute Manager Server
Features:
- Worker registration with resource tracking
- Fair job scheduling with priority queue
- Load balancing based on worker capacity
- Health monitoring with heartbeat
- Real-time statistics
"""

import socket
import threading
import json
import os
import sys
import time
import base64
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database

# Configuration
CONFIG = {
    'host': os.getenv('SERVER_HOST', '0.0.0.0'),
    'port': int(os.getenv('SERVER_PORT', 9999)),
    'heartbeat_timeout': 60,  # seconds before marking worker offline
    'max_job_retries': 3,
    'job_timeout_buffer': 30,  # extra seconds for network overhead
}


class WorkerManager:
    """Manages connected workers and their state"""

    def __init__(self):
        self.workers = {}  # worker_id -> worker_info
        self.connections = {}  # worker_id -> socket connection
        self.lock = threading.RLock()

    def register(self, worker_id, name, owner_id, specs, conn, addr):
        """Register a new worker"""
        with self.lock:
            self.workers[worker_id] = {
                'id': worker_id,
                'name': name,
                'owner_id': owner_id,
                'specs': specs,
                'status': 'online',
                'current_job': None,
                'last_heartbeat': datetime.now(),
                'address': addr,
                'jobs_completed': 0
            }
            self.connections[worker_id] = conn
            database.update_worker_status(worker_id, 'online', f"{addr[0]}:{addr[1]}")
            print(f"[WORKER+] {name} ({worker_id[:8]}) connected from {addr[0]}")

    def update_heartbeat(self, worker_id):
        """Update worker's last heartbeat time"""
        with self.lock:
            if worker_id in self.workers:
                self.workers[worker_id]['last_heartbeat'] = datetime.now()
                self.workers[worker_id]['status'] = 'online'

    def set_worker_busy(self, worker_id, job_id):
        """Mark worker as busy with a job"""
        with self.lock:
            if worker_id in self.workers:
                self.workers[worker_id]['status'] = 'busy'
                self.workers[worker_id]['current_job'] = job_id

    def set_worker_idle(self, worker_id):
        """Mark worker as idle"""
        with self.lock:
            if worker_id in self.workers:
                self.workers[worker_id]['status'] = 'online'
                self.workers[worker_id]['current_job'] = None
                self.workers[worker_id]['jobs_completed'] += 1

    def disconnect(self, worker_id):
        """Handle worker disconnection"""
        with self.lock:
            if worker_id in self.workers:
                name = self.workers[worker_id]['name']
                del self.workers[worker_id]
                if worker_id in self.connections:
                    try:
                        self.connections[worker_id].close()
                    except Exception:
                        pass
                    del self.connections[worker_id]
                database.update_worker_status(worker_id, 'offline')
                print(f"[WORKER-] {name} ({worker_id[:8]}) disconnected")

    def get_idle_workers(self):
        """Get list of idle workers"""
        with self.lock:
            return [w for w in self.workers.values() if w['status'] == 'online']

    def get_worker(self, worker_id):
        """Get worker info by ID"""
        with self.lock:
            return self.workers.get(worker_id)

    def get_connection(self, worker_id):
        """Get socket connection for worker"""
        with self.lock:
            return self.connections.get(worker_id)

    def get_stats(self):
        """Get worker statistics"""
        with self.lock:
            total = len(self.workers)
            online = sum(1 for w in self.workers.values() if w['status'] == 'online')
            busy = sum(1 for w in self.workers.values() if w['status'] == 'busy')
            return {'total': total, 'online': online, 'busy': busy}

    def check_timeouts(self):
        """Check for timed-out workers"""
        timeout_threshold = datetime.now() - timedelta(seconds=CONFIG['heartbeat_timeout'])
        timed_out = []
        with self.lock:
            for worker_id, worker in list(self.workers.items()):
                if worker['last_heartbeat'] < timeout_threshold:
                    timed_out.append(worker_id)
        for worker_id in timed_out:
            print(f"[TIMEOUT] Worker {worker_id[:8]} timed out")
            self.disconnect(worker_id)


class JobScheduler:
    """Handles job scheduling and assignment"""

    def __init__(self, worker_manager):
        self.worker_manager = worker_manager
        self.pending_jobs = {}  # job_id -> job_info
        self.lock = threading.RLock()

    def get_next_job_for_worker(self, worker_id):
        """Get the best matching job for a worker"""
        worker = self.worker_manager.get_worker(worker_id)
        if not worker:
            return None

        # Get job from database
        job = database.get_next_job_for_worker(worker_id)
        if job:
            self.worker_manager.set_worker_busy(worker_id, job['id'])
            return {
                'type': 'job',
                'job_id': job['id'],
                'title': job['title'],
                'code': job['code'],
                'requirements': job['requirements'],
                'timeout': job['timeout_seconds'],
                'credit_reward': job['credit_reward']
            }
        return None

    def complete_job(self, job_id, worker_id, success, output, error):
        """Handle job completion"""
        self.worker_manager.set_worker_idle(worker_id)
        database.complete_job(job_id, output, success, error)
        return True


class ManagerServer:
    """Main server that coordinates workers and jobs"""

    def __init__(self):
        self.worker_manager = WorkerManager()
        self.scheduler = JobScheduler(self.worker_manager)
        self.running = True
        self.server_socket = None

    def _send_message(self, conn, data):
        """Send JSON message to client"""
        try:
            msg = json.dumps(data).encode()
            header = str(len(msg)).zfill(10).encode()
            conn.send(header + msg)
            return True
        except Exception as e:
            print(f"[ERROR] Send failed: {e}")
            return False

    def _receive_message(self, conn):
        """Receive JSON message from client"""
        try:
            header = conn.recv(10).decode()
            if not header:
                print("[DEBUG] Empty header received")
                return None
            size = int(header)
            if size == 0:
                return None
            print(f"[DEBUG] Receiving message of size {size}")
            data = b''
            while len(data) < size:
                chunk = conn.recv(min(65536, size - len(data)))  # Larger chunk size
                if not chunk:
                    print("[DEBUG] No chunk received")
                    return None
                data += chunk
            print(f"[DEBUG] Received full message, parsing JSON...")
            return json.loads(data.decode())
        except Exception as e:
            print(f"[DEBUG] Receive exception: {e}")
            return None

    def handle_worker(self, conn, addr):
        """Handle a connected worker"""
        worker_id = None
        try:
            # Set socket options for better reliability
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            conn.settimeout(120)  # 2 minute timeout for receive operations

            # Wait for registration message
            msg = self._receive_message(conn)
            if not msg or msg.get('type') != 'register':
                conn.close()
                return

            name = msg.get('name', 'Unknown')
            owner_token = msg.get('owner_token', '')
            specs = msg.get('specs', {})

            # Verify owner token and get owner_id
            owner_id = self._verify_owner(owner_token)

            # Register worker in database
            worker_id = database.register_worker(name, owner_id, specs)

            # Register in memory
            self.worker_manager.register(worker_id, name, owner_id, specs, conn, addr)

            # Send confirmation
            self._send_message(conn, {
                'type': 'registered',
                'worker_id': worker_id,
                'message': f'Welcome {name}!'
            })

            # Main loop - handle worker messages
            while self.running:
                msg = self._receive_message(conn)
                if not msg:
                    break

                msg_type = msg.get('type')

                if msg_type == 'heartbeat':
                    self.worker_manager.update_heartbeat(worker_id)

                elif msg_type == 'request_job':
                    job = self.scheduler.get_next_job_for_worker(worker_id)
                    if job:
                        self._send_message(conn, job)
                    else:
                        self._send_message(conn, {'type': 'no_job'})

                elif msg_type == 'job_result':
                    job_id = msg.get('job_id')
                    success = msg.get('success', False)
                    output = msg.get('output', '')
                    error = msg.get('error')
                    files = msg.get('files', [])

                    print(f"[DEBUG] Received job result for {job_id[:8]}, output length: {len(output)}")

                    try:
                        # Save output files if any
                        if files:
                            print(f"[DEBUG] Saving {len(files)} files...")
                            self._save_job_files(job_id, files)

                        print(f"[DEBUG] Completing job in database...")
                        self.scheduler.complete_job(job_id, worker_id, success, output, error)
                        print(f"[JOB] {job_id[:8]} completed: {'SUCCESS' if success else 'FAILED'} ({len(files)} files)")
                    except Exception as e:
                        print(f"[ERROR] Failed to save job result: {e}")
                        import traceback
                        traceback.print_exc()

                    # Send acknowledgment to worker
                    print(f"[DEBUG] Sending acknowledgment...")
                    ack_sent = self._send_message(conn, {'type': 'job_received', 'job_id': job_id})
                    print(f"[DEBUG] Acknowledgment sent: {ack_sent}")

                elif msg_type == 'disconnect':
                    break

        except Exception as e:
            print(f"[ERROR] Worker handler: {e}")
        finally:
            if worker_id:
                self.worker_manager.disconnect(worker_id)

    def _verify_owner(self, token):
        """Verify owner token and return user_id"""
        if not token:
            return None
        # In production, this would verify a JWT or session token
        # For now, we'll look up by username as a simple demo
        user = database.get_user_by_username(token)
        if user:
            return user['id']
        return None

    def _save_job_files(self, job_id, files):
        """Save output files from completed job"""
        output_dir = os.path.join(os.path.dirname(__file__), 'job_outputs', job_id)
        os.makedirs(output_dir, exist_ok=True)

        for file_info in files:
            filename = file_info.get('filename', 'unknown')
            content_b64 = file_info.get('content', '')

            try:
                content = base64.b64decode(content_b64)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(content)
                print(f"[FILE] Saved: {filename} for job {job_id[:8]}")
            except Exception as e:
                print(f"[ERROR] Failed to save {filename}: {e}")

    def health_monitor(self):
        """Background thread to monitor worker health"""
        while self.running:
            self.worker_manager.check_timeouts()
            time.sleep(30)

    def start(self):
        """Start the manager server"""
        database.init_db()

        # Start health monitor
        health_thread = threading.Thread(target=self.health_monitor, daemon=True)
        health_thread.start()

        # Start server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((CONFIG['host'], CONFIG['port']))
        self.server_socket.listen(50)

        print(f"\n{'='*50}")
        print(f"  P2P Campus Compute Manager")
        print(f"  Listening on {CONFIG['host']}:{CONFIG['port']}")
        print(f"{'='*50}\n")

        try:
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    thread = threading.Thread(
                        target=self.handle_worker,
                        args=(conn, addr),
                        daemon=True
                    )
                    thread.start()
                except Exception as e:
                    if self.running:
                        print(f"[ERROR] Accept failed: {e}")
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
        finally:
            self.running = False
            if self.server_socket:
                self.server_socket.close()


def start_server():
    """Entry point"""
    server = ManagerServer()
    server.start()


if __name__ == "__main__":
    start_server()
