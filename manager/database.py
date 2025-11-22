"""
Enhanced Database Module for P2P Campus Compute Network
Supports: Users, Workers, Jobs, Credits, and Resource Tracking
"""

import sqlite3
import os
import json
import uuid
from datetime import datetime
from contextlib import contextmanager

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "campus_compute.db")


@contextmanager
def get_db():
    """Thread-safe database connection context manager"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')  # 30 second timeout
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize all database tables"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table - authentication and credits
        # Roles: 'coordinator' (admin), 'worker' (contributes compute), 'user' (submits jobs)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                credits INTEGER DEFAULT 100,
                is_admin INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        ''')

        # Add is_admin column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
        except:
            pass  # Column already exists

        # Add role column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except:
            pass  # Column already exists

        # Workers table - registered compute nodes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_id TEXT,
                ip_address TEXT,
                status TEXT DEFAULT 'offline',
                cpu_cores INTEGER,
                cpu_model TEXT,
                ram_gb REAL,
                gpu_name TEXT,
                gpu_memory_gb REAL,
                has_docker INTEGER DEFAULT 0,
                last_heartbeat DATETIME,
                total_jobs_completed INTEGER DEFAULT 0,
                total_credits_earned INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        ''')

        # Jobs table - compute tasks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                submitter_id TEXT NOT NULL,
                worker_id TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 5,
                code TEXT NOT NULL,
                requirements TEXT,
                cpu_required INTEGER DEFAULT 1,
                ram_required_gb REAL DEFAULT 1,
                gpu_required INTEGER DEFAULT 0,
                timeout_seconds INTEGER DEFAULT 300,
                credit_cost INTEGER DEFAULT 10,
                credit_reward INTEGER DEFAULT 10,
                result_output TEXT,
                error_log TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                FOREIGN KEY (submitter_id) REFERENCES users(id),
                FOREIGN KEY (worker_id) REFERENCES workers(id)
            )
        ''')

        # Job queue for fair scheduling
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                priority INTEGER DEFAULT 5,
                queued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        ''')

        # Transaction log for credits
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credit_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                job_id TEXT,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        ''')

        # Activity logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                actor_id TEXT,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        print("[DB] Database initialized successfully")


# ==================== USER OPERATIONS ====================

def create_user(username, password_hash, email=None, role='user'):
    """Create a new user with starting credits"""
    user_id = str(uuid.uuid4())
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (id, username, password_hash, email, credits, role)
                VALUES (?, ?, ?, ?, 100, ?)
            ''', (user_id, username, password_hash, email, role))
            conn.commit()
            log_activity('user_registered', user_id, f'New {role}: {username}')
            return user_id
        except sqlite3.IntegrityError:
            return None


def get_user_by_username(username):
    """Get user by username"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        return cursor.fetchone()


def get_user_by_id(user_id):
    """Get user by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()


def update_user_credits(user_id, amount, transaction_type, job_id=None, description=None):
    """Update user credits and log transaction"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT credits FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            new_balance = user['credits'] + amount
            if new_balance < 0:
                return False, "Insufficient credits"
            cursor.execute('UPDATE users SET credits = ? WHERE id = ?', (new_balance, user_id))
            cursor.execute('''
                INSERT INTO credit_transactions (user_id, amount, transaction_type, job_id, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, transaction_type, job_id, description))
            conn.commit()
            return True, new_balance
        return False, "User not found"


def get_leaderboard(limit=10):
    """Get top contributors by credits earned"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.username, u.credits,
                   (SELECT COUNT(*) FROM workers w WHERE w.owner_id = u.id AND w.status = 'online') as active_workers,
                   (SELECT SUM(total_jobs_completed) FROM workers w WHERE w.owner_id = u.id) as jobs_completed
            FROM users u
            ORDER BY u.credits DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()


def set_user_role(user_id, role):
    """Set a user's role (coordinator, worker, user)"""
    valid_roles = ['coordinator', 'worker', 'user']
    if role not in valid_roles:
        return False
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
        # If coordinator, also set is_admin
        if role == 'coordinator':
            cursor.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_all_users():
    """Get all users (for coordinator view)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, email, credits, role, is_admin, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        ''')
        return cursor.fetchall()


def get_users_by_role(role):
    """Get users filtered by role"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE role = ?', (role,))
        return cursor.fetchall()


# ==================== WORKER OPERATIONS ====================

def register_worker(name, owner_id, specs):
    """Register a new worker node"""
    worker_id = str(uuid.uuid4())
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workers (id, name, owner_id, cpu_cores, cpu_model, ram_gb,
                                gpu_name, gpu_memory_gb, has_docker, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'offline')
        ''', (
            worker_id, name, owner_id,
            specs.get('cpu_cores', 1),
            specs.get('cpu_model', 'Unknown'),
            specs.get('ram_gb', 1),
            specs.get('gpu_name'),
            specs.get('gpu_memory_gb'),
            specs.get('has_docker', 0)
        ))
        conn.commit()
        log_activity('worker_registered', owner_id, f'Worker: {name}')
        return worker_id


def update_worker_status(worker_id, status, ip_address=None):
    """Update worker online status"""
    with get_db() as conn:
        cursor = conn.cursor()
        if ip_address:
            cursor.execute('''
                UPDATE workers SET status = ?, ip_address = ?, last_heartbeat = ?
                WHERE id = ?
            ''', (status, ip_address, datetime.now(), worker_id))
        else:
            cursor.execute('''
                UPDATE workers SET status = ?, last_heartbeat = ?
                WHERE id = ?
            ''', (status, datetime.now(), worker_id))
        conn.commit()


def get_available_workers(cpu_required=1, ram_required=1, gpu_required=0):
    """Get workers that can handle a job's requirements"""
    with get_db() as conn:
        cursor = conn.cursor()
        if gpu_required:
            cursor.execute('''
                SELECT * FROM workers
                WHERE status = 'online'
                AND cpu_cores >= ?
                AND ram_gb >= ?
                AND gpu_name IS NOT NULL
                ORDER BY total_jobs_completed ASC
            ''', (cpu_required, ram_required))
        else:
            cursor.execute('''
                SELECT * FROM workers
                WHERE status = 'online'
                AND cpu_cores >= ?
                AND ram_gb >= ?
                ORDER BY total_jobs_completed ASC
            ''', (cpu_required, ram_required))
        return cursor.fetchall()


def get_all_workers():
    """Get all registered workers"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.*, u.username as owner_name
            FROM workers w
            LEFT JOIN users u ON w.owner_id = u.id
            ORDER BY w.status DESC, w.last_heartbeat DESC
        ''')
        return cursor.fetchall()


def get_worker_by_id(worker_id):
    """Get worker by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workers WHERE id = ?', (worker_id,))
        return cursor.fetchone()


def increment_worker_stats(worker_id, credits_earned):
    """Update worker statistics after job completion"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE workers
            SET total_jobs_completed = total_jobs_completed + 1,
                total_credits_earned = total_credits_earned + ?
            WHERE id = ?
        ''', (credits_earned, worker_id))
        conn.commit()


# ==================== JOB OPERATIONS ====================

def create_job(title, submitter_id, code, requirements=None, cpu_required=1,
               ram_required=1, gpu_required=0, timeout=300, priority=5):
    """Create a new compute job"""
    job_id = str(uuid.uuid4())
    credit_cost = calculate_job_cost(cpu_required, ram_required, gpu_required, timeout)

    # Check if user has enough credits
    user = get_user_by_id(submitter_id)
    if not user or user['credits'] < credit_cost:
        return None, "Insufficient credits"

    with get_db() as conn:
        cursor = conn.cursor()

        # Deduct credits from submitter
        cursor.execute('''
            UPDATE users SET credits = credits - ? WHERE id = ?
        ''', (credit_cost, submitter_id))

        # Create job
        cursor.execute('''
            INSERT INTO jobs (id, title, submitter_id, code, requirements,
                             cpu_required, ram_required_gb, gpu_required,
                             timeout_seconds, credit_cost, credit_reward, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, title, submitter_id, code, requirements,
              cpu_required, ram_required, gpu_required, timeout,
              credit_cost, credit_cost, priority))

        # Add to queue
        cursor.execute('''
            INSERT INTO job_queue (job_id, priority)
            VALUES (?, ?)
        ''', (job_id, priority))

        # Log transaction
        cursor.execute('''
            INSERT INTO credit_transactions (user_id, amount, transaction_type, job_id, description)
            VALUES (?, ?, 'job_submitted', ?, ?)
        ''', (submitter_id, -credit_cost, job_id, f'Submitted job: {title}'))

        conn.commit()
        log_activity('job_created', submitter_id, f'Job: {title}')
        return job_id, None


def calculate_job_cost(cpu, ram, gpu, timeout):
    """Calculate credit cost based on resource requirements"""
    base_cost = 5
    cpu_cost = cpu * 2
    ram_cost = int(ram * 1)
    gpu_cost = gpu * 10
    time_cost = timeout // 60  # 1 credit per minute
    return base_cost + cpu_cost + ram_cost + gpu_cost + time_cost


def get_next_job_for_worker(worker_id):
    """Get the next job from queue that worker can handle"""
    worker = get_worker_by_id(worker_id)
    if not worker:
        return None

    with get_db() as conn:
        cursor = conn.cursor()

        # Find matching job from queue
        cursor.execute('''
            SELECT j.* FROM jobs j
            JOIN job_queue q ON j.id = q.job_id
            WHERE j.status = 'pending'
            AND j.cpu_required <= ?
            AND j.ram_required_gb <= ?
            AND (j.gpu_required = 0 OR ? IS NOT NULL)
            ORDER BY q.priority DESC, q.queued_at ASC
            LIMIT 1
        ''', (worker['cpu_cores'], worker['ram_gb'], worker['gpu_name']))

        job = cursor.fetchone()
        if job:
            # Assign job to worker
            cursor.execute('''
                UPDATE jobs SET status = 'running', worker_id = ?, started_at = ?
                WHERE id = ?
            ''', (worker_id, datetime.now(), job['id']))

            # Remove from queue
            cursor.execute('DELETE FROM job_queue WHERE job_id = ?', (job['id'],))

            conn.commit()
            log_activity('job_started', worker_id, f'Job {job["id"]} started')

        return job


def complete_job(job_id, result_output, success=True, error_log=None):
    """Mark job as completed and process rewards"""
    import time
    max_retries = 3

    for attempt in range(max_retries):
        try:
            with get_db() as conn:
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
                job = cursor.fetchone()

                if not job:
                    return False

                status = 'completed' if success else 'failed'

                # Update job
                cursor.execute('''
                    UPDATE jobs SET status = ?, result_output = ?, error_log = ?, completed_at = ?
                    WHERE id = ?
                ''', (status, result_output, error_log, datetime.now(), job_id))

                if success and job['worker_id']:
                    # Reward worker owner
                    worker = get_worker_by_id(job['worker_id'])
                    if worker and worker['owner_id']:
                        cursor.execute('''
                            UPDATE users SET credits = credits + ? WHERE id = ?
                        ''', (job['credit_reward'], worker['owner_id']))

                        cursor.execute('''
                            INSERT INTO credit_transactions (user_id, amount, transaction_type, job_id, description)
                            VALUES (?, ?, 'job_completed', ?, ?)
                        ''', (worker['owner_id'], job['credit_reward'], job_id, f'Completed job: {job["title"]}'))

                        # Update worker stats
                        cursor.execute('''
                            UPDATE workers
                            SET total_jobs_completed = total_jobs_completed + 1,
                                total_credits_earned = total_credits_earned + ?
                            WHERE id = ?
                        ''', (job['credit_reward'], job['worker_id']))

                conn.commit()
                log_activity('job_completed', job['worker_id'], f'Job {job_id}: {status}')
                return True
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) and attempt < max_retries - 1:
                print(f"[DB] Database locked, retrying ({attempt + 1}/{max_retries})...")
                time.sleep(0.5)
            else:
                raise
    return False


def get_job_by_id(job_id):
    """Get job details"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
        return cursor.fetchone()


def get_jobs_by_status(status=None, limit=50):
    """Get jobs filtered by status"""
    with get_db() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute('''
                SELECT j.*, u.username as submitter_name, w.name as worker_name
                FROM jobs j
                LEFT JOIN users u ON j.submitter_id = u.id
                LEFT JOIN workers w ON j.worker_id = w.id
                WHERE j.status = ?
                ORDER BY j.created_at DESC
                LIMIT ?
            ''', (status, limit))
        else:
            cursor.execute('''
                SELECT j.*, u.username as submitter_name, w.name as worker_name
                FROM jobs j
                LEFT JOIN users u ON j.submitter_id = u.id
                LEFT JOIN workers w ON j.worker_id = w.id
                ORDER BY j.created_at DESC
                LIMIT ?
            ''', (limit,))
        return cursor.fetchall()


def get_user_jobs(user_id, limit=20):
    """Get jobs submitted by a user"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM jobs WHERE submitter_id = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        return cursor.fetchall()


def get_queue_stats():
    """Get job queue statistics"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                (SELECT COUNT(*) FROM jobs WHERE status = 'pending') as pending,
                (SELECT COUNT(*) FROM jobs WHERE status = 'running') as running,
                (SELECT COUNT(*) FROM jobs WHERE status = 'completed') as completed,
                (SELECT COUNT(*) FROM jobs WHERE status = 'failed') as failed,
                (SELECT COUNT(*) FROM workers WHERE status = 'online') as online_workers
        ''')
        return cursor.fetchone()


# ==================== ACTIVITY LOGGING ====================

def log_activity(event_type, actor_id, details):
    """Log system activity"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_logs (event_type, actor_id, details)
            VALUES (?, ?, ?)
        ''', (event_type, actor_id, details))
        conn.commit()


def get_recent_activity(limit=20):
    """Get recent activity log"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM activity_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()


# ==================== LEGACY SUPPORT ====================

def save_log(worker_ip, task_name, output_log):
    """Legacy function for backward compatibility"""
    log_activity('legacy_job', None, f'{worker_ip} completed {task_name}')


def add_credits(username, amount):
    """Legacy function for backward compatibility"""
    user = get_user_by_username(username)
    if user:
        update_user_credits(user['id'], amount, 'legacy_reward', description='Legacy credit addition')
    else:
        # Create user if doesn't exist (legacy behavior)
        import bcrypt
        password_hash = bcrypt.hashpw('temp123'.encode(), bcrypt.gensalt()).decode()
        user_id = create_user(username, password_hash)
        if user_id:
            update_user_credits(user_id, amount - 100, 'legacy_reward')  # -100 because they start with 100


# ==================== ADMIN FUNCTIONS ====================

def set_user_admin(user_id, is_admin=True):
    """Set a user as admin or remove admin"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_admin = ? WHERE id = ?', (1 if is_admin else 0, user_id))
        conn.commit()
        return cursor.rowcount > 0


def make_first_user_admin():
    """Make the first registered user an admin"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users ORDER BY created_at LIMIT 1')
        row = cursor.fetchone()
        if row:
            cursor.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (row['id'],))
            conn.commit()
            return True
    return False


def clear_job_history():
    """Clear all job history"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM jobs')
        cursor.execute('DELETE FROM job_queue')
        cursor.execute('DELETE FROM activity_logs')
        conn.commit()
        return True


def clear_workers():
    """Clear all workers"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM workers')
        conn.commit()
        return True


def remove_worker(worker_id):
    """Remove a specific worker"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM workers WHERE id = ?', (worker_id,))
        conn.commit()
        return cursor.rowcount > 0


def pause_worker(worker_id):
    """Pause a worker (set to paused status)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE workers SET status = ? WHERE id = ?',
            ('paused', worker_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def resume_worker(worker_id):
    """Resume a paused worker"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE workers SET status = ? WHERE id = ?',
            ('online', worker_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_user_workers(user_id):
    """Get workers owned by a user"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM workers
            WHERE owner_id = ?
            ORDER BY last_heartbeat DESC
        ''', (user_id,))
        return cursor.fetchall()


if __name__ == "__main__":
    init_db()
    print("Database initialized!")
