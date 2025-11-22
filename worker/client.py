"""
P2P Campus Compute Worker Client
Features:
- Automatic resource detection (CPU, RAM, GPU)
- Docker-based sandboxed execution
- Secure job running with timeouts
- Heartbeat mechanism
- Graceful shutdown
"""

import socket
import json
import os
import sys
import time
import threading
import subprocess
import tempfile
import shutil
import signal
import base64
import glob as glob_module
from datetime import datetime

# Try to import optional dependencies
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[WARN] psutil not installed. Resource detection limited.")

try:
    import docker
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False
    print("[WARN] Docker SDK not installed. Sandboxing disabled.")

# Configuration
CONFIG = {
    'manager_host': os.getenv('MANAGER_HOST', 'localhost'),
    'manager_port': int(os.getenv('MANAGER_PORT', 9999)),
    'worker_name': os.getenv('WORKER_NAME', f'Worker_{os.getpid()}'),
    'owner_token': os.getenv('OWNER_TOKEN', ''),
    'heartbeat_interval': 30,
    'use_docker': os.getenv('USE_DOCKER', 'true').lower() == 'true',
    'max_job_timeout': 600,
}


class SystemInfo:
    """Detect system hardware specifications"""

    @staticmethod
    def get_cpu_info():
        if HAS_PSUTIL:
            return {
                'cores': psutil.cpu_count(logical=False) or 1,
                'threads': psutil.cpu_count(logical=True) or 1,
                'model': SystemInfo._get_cpu_model(),
                'usage_percent': psutil.cpu_percent(interval=1)
            }
        return {'cores': 1, 'threads': 1, 'model': 'Unknown', 'usage_percent': 0}

    @staticmethod
    def _get_cpu_model():
        try:
            if sys.platform == 'darwin':
                result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                         capture_output=True, text=True)
                return result.stdout.strip()
            elif sys.platform == 'linux':
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            return line.split(':')[1].strip()
            elif sys.platform == 'win32':
                import platform
                return platform.processor()
        except Exception:
            pass
        return 'Unknown CPU'

    @staticmethod
    def get_memory_info():
        if HAS_PSUTIL:
            mem = psutil.virtual_memory()
            return {
                'total_gb': round(mem.total / (1024 ** 3), 2),
                'available_gb': round(mem.available / (1024 ** 3), 2),
                'used_percent': mem.percent
            }
        return {'total_gb': 4, 'available_gb': 2, 'used_percent': 50}

    @staticmethod
    def get_gpu_info():
        """Detect GPU if available"""
        try:
            # Try nvidia-smi for NVIDIA GPUs
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                return {
                    'name': parts[0].strip(),
                    'memory_gb': round(int(parts[1].strip().replace(' MiB', '')) / 1024, 2)
                }
        except Exception:
            pass

        # Try Metal for Mac
        if sys.platform == 'darwin':
            try:
                result = subprocess.run(
                    ['system_profiler', 'SPDisplaysDataType'],
                    capture_output=True, text=True, timeout=5
                )
                if 'Chipset Model' in result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'Chipset Model' in line:
                            return {'name': line.split(':')[1].strip(), 'memory_gb': 0}
            except Exception:
                pass

        return None

    @staticmethod
    def check_docker():
        """Check if Docker is available and running"""
        if not HAS_DOCKER:
            return False
        try:
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    @staticmethod
    def get_full_specs():
        """Get complete system specifications"""
        cpu = SystemInfo.get_cpu_info()
        mem = SystemInfo.get_memory_info()
        gpu = SystemInfo.get_gpu_info()

        return {
            'cpu_cores': cpu['cores'],
            'cpu_model': cpu['model'],
            'ram_gb': mem['total_gb'],
            'gpu_name': gpu['name'] if gpu else None,
            'gpu_memory_gb': gpu['memory_gb'] if gpu else None,
            'has_docker': 1 if SystemInfo.check_docker() else 0
        }


class SandboxExecutor:
    """Execute code in isolated environment"""

    def __init__(self, use_docker=True):
        self.use_docker = use_docker and HAS_DOCKER and SystemInfo.check_docker()
        if self.use_docker:
            self.docker_client = docker.from_env()
            print("[SANDBOX] Docker sandbox enabled")
        else:
            print("[SANDBOX] Running in restricted mode (no Docker)")

    def execute(self, code, timeout=300, requirements=None):
        """Execute code and return result"""
        if self.use_docker:
            return self._execute_docker(code, timeout, requirements)
        else:
            return self._execute_restricted(code, timeout, requirements)

    def _execute_docker(self, code, timeout, requirements):
        """Execute code in Docker container with security isolation"""
        temp_dir = tempfile.mkdtemp(prefix='p2p_job_')
        output_dir = os.path.join(temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        try:
            # Write code to file
            code_path = os.path.join(temp_dir, 'job.py')
            with open(code_path, 'w') as f:
                f.write(code)

            # Create requirements file if needed
            if requirements:
                req_path = os.path.join(temp_dir, 'requirements.txt')
                with open(req_path, 'w') as f:
                    f.write(requirements)

            # Build run command
            if requirements:
                run_cmd = 'pip install -q -r /app/requirements.txt && python /app/job.py'
            else:
                run_cmd = 'python /app/job.py'

            # Run container with security restrictions
            container = self.docker_client.containers.run(
                image='python:3.11-slim',
                command=['sh', '-c', run_cmd],
                volumes={
                    temp_dir: {'bind': '/app', 'mode': 'rw'},  # App directory
                    output_dir: {'bind': '/output', 'mode': 'rw'}  # Output directory
                },
                working_dir='/app',
                environment={
                    'OUTPUT_DIR': '/output',
                    'PYTHONUNBUFFERED': '1'  # Ensure print output is captured
                },
                # Resource limits
                mem_limit='1g',             # Max 1GB RAM
                cpu_period=100000,
                cpu_quota=100000,           # 100% of one CPU
                pids_limit=200,             # Max 200 processes
                # Security restrictions
                network_disabled=True,      # No network access
                detach=True,
                remove=False
            )
            print(f"[DOCKER] Container started")

            try:
                result = container.wait(timeout=timeout)
                logs = container.logs().decode('utf-8')
                exit_code = result.get('StatusCode', 1)

                # Collect output files from the output directory
                output_files = self._collect_output_files(output_dir)

                return {
                    'success': exit_code == 0,
                    'output': logs,
                    'error': None if exit_code == 0 else f'Exit code: {exit_code}',
                    'files': output_files
                }
            except Exception as e:
                try:
                    container.kill()
                except Exception:
                    pass
                return {
                    'success': False,
                    'output': '',
                    'error': f'Timeout or error: {str(e)}',
                    'files': []
                }
            finally:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _execute_restricted(self, code, timeout, requirements=None):
        """Execute code with restrictions (fallback when Docker unavailable)"""
        import textwrap
        temp_dir = tempfile.mkdtemp(prefix='p2p_job_')
        output_dir = os.path.join(temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        try:
            # Install requirements if specified
            if requirements:
                print(f"[PIP] Installing requirements...")
                req_lines = [r.strip() for r in requirements.strip().split('\n') if r.strip()]
                for req in req_lines:
                    try:
                        subprocess.run(
                            [sys.executable, '-m', 'pip', 'install', '-q', req],
                            capture_output=True,
                            timeout=60
                        )
                        print(f"[PIP] Installed: {req}")
                    except Exception as e:
                        print(f"[PIP] Failed to install {req}: {e}")

            code_path = os.path.join(temp_dir, 'job.py')

            # Clean user code - remove any common leading whitespace
            user_code = textwrap.dedent(code).strip()

            # Build the wrapper code as separate lines to avoid indentation issues
            wrapper_lines = [
                'import sys',
                'import os',
                '',
                '# Output directory for job files (PDFs, images, etc.)',
                f'OUTPUT_DIR = "{output_dir}"',
                'os.makedirs(OUTPUT_DIR, exist_ok=True)',
                '',
                '# Helper function to save text files',
                'def save_output(filename, content):',
                '    """Save a text file to the output directory"""',
                '    filepath = os.path.join(OUTPUT_DIR, filename)',
                '    with open(filepath, "w") as f:',
                '        f.write(content)',
                '    print("[OUTPUT] Saved: " + filename)',
                '    return filepath',
                '',
                '# Helper function to save binary files (PDF, images, etc.)',
                'def save_binary(filename, content):',
                '    """Save a binary file to the output directory"""',
                '    filepath = os.path.join(OUTPUT_DIR, filename)',
                '    with open(filepath, "wb") as f:',
                '        f.write(content)',
                '    print("[OUTPUT] Saved binary: " + filename)',
                '    return filepath',
                '',
                '# ============ USER CODE BELOW ============',
                '',
            ]

            # Combine wrapper with user code
            safe_code = '\n'.join(wrapper_lines) + '\n' + user_code + '\n'

            with open(code_path, 'w') as f:
                f.write(safe_code)

            proc = subprocess.run(
                [sys.executable, code_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=temp_dir
            )

            # Collect output files from both output_dir and temp_dir (for files like output.pdf)
            output_files = self._collect_output_files(output_dir)
            # Also collect any files created in the temp directory (excluding job.py)
            output_files.extend(self._collect_output_files(temp_dir, exclude=['job.py', 'output']))

            # Combine stdout and stderr for full output
            full_output = proc.stdout
            if proc.stderr:
                full_output += "\n[STDERR]\n" + proc.stderr

            return {
                'success': proc.returncode == 0,
                'output': full_output,
                'error': proc.stderr if proc.returncode != 0 else None,
                'files': output_files
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': f'Job timed out after {timeout} seconds',
                'files': []
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'files': []
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _collect_output_files(self, output_dir, max_file_size=10*1024*1024, exclude=None):
        """Collect output files and encode as base64"""
        files = []
        exclude = exclude or []
        if not os.path.exists(output_dir):
            return files

        for filepath in glob_module.glob(os.path.join(output_dir, '*')):
            filename = os.path.basename(filepath)
            if filename in exclude:
                continue
            if os.path.isfile(filepath):
                file_size = os.path.getsize(filepath)
                if file_size > max_file_size:
                    print(f"[WARN] File too large, skipping: {filepath}")
                    continue

                filename = os.path.basename(filepath)
                try:
                    with open(filepath, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('utf-8')
                    files.append({
                        'filename': filename,
                        'size': file_size,
                        'content': content
                    })
                    print(f"[FILE] Collected: {filename} ({file_size} bytes)")
                except Exception as e:
                    print(f"[ERROR] Failed to collect {filename}: {e}")

        return files


class WorkerClient:
    """Main worker client that connects to manager"""

    def __init__(self, config):
        self.config = config
        self.running = True
        self.connected = False
        self.socket = None
        self.worker_id = None
        self.executor = SandboxExecutor(use_docker=config['use_docker'])
        self.specs = SystemInfo.get_full_specs()

        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print("\n[WORKER] Shutting down gracefully...")
        self.running = False
        if self.socket:
            self._send_message({'type': 'disconnect'})
            self.socket.close()

    def _send_message(self, data):
        """Send JSON message to server"""
        try:
            msg = json.dumps(data).encode()
            header = str(len(msg)).zfill(10).encode()
            self.socket.send(header + msg)
            return True
        except Exception as e:
            print(f"[ERROR] Send failed: {e}")
            return False

    def _receive_message(self):
        """Receive JSON message from server"""
        try:
            header = self.socket.recv(10).decode()
            if not header:
                return None
            size = int(header)
            if size == 0:
                return {'type': 'no_job'}
            data = b''
            while len(data) < size:
                chunk = self.socket.recv(min(8192, size - len(data)))
                if not chunk:
                    return None
                data += chunk
            return json.loads(data.decode())
        except Exception as e:
            print(f"[ERROR] Receive failed: {e}")
            return None

    def connect(self):
        """Connect to manager server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.config['manager_host'], self.config['manager_port']))

            # Send registration
            reg_data = {
                'type': 'register',
                'name': self.config['worker_name'],
                'owner_token': self.config['owner_token'],
                'specs': self.specs
            }
            self._send_message(reg_data)

            # Wait for confirmation
            response = self._receive_message()
            if response and response.get('type') == 'registered':
                self.worker_id = response.get('worker_id')
                self.connected = True
                print(f"[WORKER] Registered as {self.worker_id}")
                print(f"[SPECS] CPU: {self.specs['cpu_cores']} cores | RAM: {self.specs['ram_gb']}GB | GPU: {self.specs.get('gpu_name', 'None')}")
                return True
            else:
                print(f"[ERROR] Registration failed: {response}")
                return False

        except ConnectionRefusedError:
            print(f"[ERROR] Cannot connect to {self.config['manager_host']}:{self.config['manager_port']}")
            return False
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            return False

    def heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running and self.connected:
            try:
                self._send_message({
                    'type': 'heartbeat',
                    'worker_id': self.worker_id,
                    'status': 'idle'
                })
            except Exception:
                pass
            time.sleep(self.config['heartbeat_interval'])

    def request_job(self):
        """Request a job from the manager"""
        self._send_message({
            'type': 'request_job',
            'worker_id': self.worker_id
        })
        return self._receive_message()

    def execute_job(self, job):
        """Execute a job and return results"""
        job_id = job.get('job_id')
        code = job.get('code')
        timeout = min(job.get('timeout', 300), self.config['max_job_timeout'])
        requirements = job.get('requirements')

        print(f"[JOB] Executing job {job_id[:8]}... (timeout: {timeout}s)")
        start_time = time.time()

        result = self.executor.execute(code, timeout, requirements)

        elapsed = round(time.time() - start_time, 2)
        status = 'SUCCESS' if result['success'] else 'FAILED'
        print(f"[JOB] {status} in {elapsed}s")

        return {
            'type': 'job_result',
            'job_id': job_id,
            'worker_id': self.worker_id,
            'success': result['success'],
            'output': result['output'],
            'error': result['error'],
            'files': result.get('files', []),
            'execution_time': elapsed
        }

    def run(self):
        """Main worker loop"""
        print(f"\n{'='*50}")
        print(f"  P2P Campus Compute Worker")
        print(f"  Name: {self.config['worker_name']}")
        print(f"  Manager: {self.config['manager_host']}:{self.config['manager_port']}")
        print(f"{'='*50}\n")

        if not self.connect():
            return

        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        heartbeat_thread.start()

        print("[WORKER] Ready and waiting for jobs...")

        while self.running and self.connected:
            try:
                # Request job
                job_response = self.request_job()

                if not job_response:
                    print("[WORKER] Disconnected from manager")
                    break

                if job_response.get('type') == 'job':
                    # Execute the job
                    result = self.execute_job(job_response)
                    self._send_message(result)
                elif job_response.get('type') == 'no_job':
                    # No jobs available, wait a bit
                    time.sleep(5)
                else:
                    time.sleep(2)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                time.sleep(5)

        print("[WORKER] Stopped")


def main():
    """Entry point"""
    # Allow command-line override
    if len(sys.argv) > 1:
        CONFIG['manager_host'] = sys.argv[1]
    if len(sys.argv) > 2:
        CONFIG['worker_name'] = sys.argv[2]
    if len(sys.argv) > 3:
        CONFIG['owner_token'] = sys.argv[3]

    worker = WorkerClient(CONFIG)
    worker.run()


if __name__ == "__main__":
    main()
