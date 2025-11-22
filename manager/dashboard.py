"""
P2P Campus Compute Dashboard
Features:
- User authentication (login/register)
- Real-time updates via WebSocket
- Job submission and monitoring
- Worker management
- Leaderboard and credits
"""

import os
import sys
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database

# Try to import bcrypt
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    print("[WARN] bcrypt not installed. Using simple password hashing (NOT for production!)")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'campus-compute-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'tasks')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==================== AUTHENTICATION ====================

def hash_password(password):
    """Hash a password"""
    if HAS_BCRYPT:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    # Simple fallback (NOT secure - only for demo)
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, password_hash):
    """Verify a password against its hash"""
    if HAS_BCRYPT:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest() == password_hash


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        user = database.get_user_by_id(session['user_id'])
        if not user or not user['is_admin']:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            user = database.get_user_by_id(session['user_id'])
            if not user:
                flash('User not found.', 'error')
                return redirect(url_for('login'))
            user_role = user['role'] if user['role'] else 'user'
            # Coordinators can access everything
            if user_role == 'coordinator' or user_role in roles:
                return f(*args, **kwargs)
            flash(f'Access denied. Required role: {", ".join(roles)}', 'error')
            return redirect(url_for('dashboard_redirect'))
        return decorated_function
    return decorator


def get_current_user():
    """Get current logged-in user"""
    if 'user_id' in session:
        return database.get_user_by_id(session['user_id'])
    return None


# ==================== AUTH ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')

        user = database.get_user_by_username(username)
        if user and verify_password(password, user['password_hash']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role'] if user['role'] else 'user'
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard_redirect'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'user')

        # Validate role
        if role not in ['coordinator', 'worker', 'user']:
            role = 'user'

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')

        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        password_hash = hash_password(password)
        user_id = database.create_user(username, password_hash, email or None, role)

        if user_id:
            # If coordinator, also set as admin
            if role == 'coordinator':
                database.set_user_role(user_id, 'coordinator')
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = role
            flash(f'Welcome to CampusGrid, {username}! You registered as {role}. You received 100 credits to start.', 'success')
            return redirect(url_for('dashboard_redirect'))
        else:
            flash('Username already taken.', 'error')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ==================== MAIN ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard_redirect():
    """Redirect users to their role-specific dashboard"""
    user = get_current_user()
    role = user['role'] if user and user['role'] else 'user'

    if role == 'coordinator':
        return redirect(url_for('coordinator_dashboard'))
    elif role == 'worker':
        return redirect(url_for('worker_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))


@app.route('/')
@login_required
def index():
    """Main index - redirects to role-specific dashboard"""
    return redirect(url_for('dashboard_redirect'))


@app.route('/coordinator')
@role_required('coordinator')
def coordinator_dashboard():
    """Coordinator dashboard - full system overview and management"""
    user = get_current_user()
    stats = database.get_queue_stats()
    leaderboard = database.get_leaderboard(10)
    recent_jobs = database.get_jobs_by_status(limit=20)
    workers = database.get_all_workers()
    all_users = database.get_all_users()

    return render_template('coordinator_dashboard.html',
                           user=user,
                           stats=stats,
                           leaderboard=leaderboard,
                           recent_jobs=recent_jobs,
                           workers=workers,
                           all_users=all_users)


@app.route('/worker-dashboard')
@role_required('worker')
def worker_dashboard():
    """Worker dashboard - manage own workers and view earnings"""
    user = get_current_user()
    my_workers = database.get_workers_with_current_jobs(user['id'])
    stats = database.get_queue_stats()

    # Calculate total earnings from workers
    total_earnings = sum(w['total_credits_earned'] or 0 for w in my_workers)
    total_jobs = sum(w['total_jobs_completed'] or 0 for w in my_workers)

    return render_template('worker_dashboard.html',
                           user=user,
                           workers=my_workers,
                           stats=stats,
                           total_earnings=total_earnings,
                           total_jobs=total_jobs)


@app.route('/user-dashboard')
@role_required('user')
def user_dashboard():
    """User dashboard - submit jobs and view results"""
    user = get_current_user()
    my_jobs = database.get_user_jobs(user['id'], limit=20)
    stats = database.get_queue_stats()

    return render_template('user_dashboard.html',
                           user=user,
                           jobs=my_jobs,
                           stats=stats)


@app.route('/jobs')
@login_required
def jobs():
    user = get_current_user()
    status_filter = request.args.get('status')
    jobs_list = database.get_jobs_by_status(status_filter, limit=50)
    return render_template('jobs.html', user=user, jobs=jobs_list, status_filter=status_filter)


@app.route('/my-jobs')
@login_required
def my_jobs():
    user = get_current_user()
    jobs_list = database.get_user_jobs(user['id'], limit=50)
    return render_template('my_jobs.html', user=user, jobs=jobs_list)


@app.route('/workers')
@login_required
def workers():
    user = get_current_user()
    workers_list = database.get_all_workers()
    return render_template('workers.html', user=user, workers=workers_list)


@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_job():
    user = get_current_user()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        code = request.form.get('code', '')
        requirements = request.form.get('requirements', '').strip()

        try:
            cpu_required = int(request.form.get('cpu', 1))
            ram_required = float(request.form.get('ram', 1))
            gpu_required = int(request.form.get('gpu', 0))
            timeout = int(request.form.get('timeout', 300))
            priority = int(request.form.get('priority', 5))
        except (ValueError, TypeError):
            flash('Invalid numeric values provided.', 'error')
            return render_template('submit.html', user=user)

        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                code = file.read().decode('utf-8')

        if not title:
            flash('Job title is required.', 'error')
            return render_template('submit.html', user=user)

        if not code:
            flash('Job code is required.', 'error')
            return render_template('submit.html', user=user)

        # Calculate cost
        cost = database.calculate_job_cost(cpu_required, ram_required, gpu_required, timeout)

        if user['credits'] < cost:
            flash(f'Insufficient credits. This job costs {cost} credits, you have {user["credits"]}.', 'error')
            return render_template('submit.html', user=user)

        # Create job
        job_id, error = database.create_job(
            title=title,
            submitter_id=user['id'],
            code=code,
            requirements=requirements or None,
            cpu_required=cpu_required,
            ram_required=ram_required,
            gpu_required=gpu_required,
            timeout=timeout,
            priority=priority
        )

        if job_id:
            flash(f'Job submitted successfully! Cost: {cost} credits.', 'success')
            # Notify connected clients
            socketio.emit('job_update', {'type': 'new_job', 'job_id': job_id})
            return redirect(url_for('my_jobs'))
        else:
            flash(f'Failed to submit job: {error}', 'error')

    return render_template('submit.html', user=user)


@app.route('/job/<job_id>')
@login_required
def job_detail(job_id):
    user = get_current_user()
    job = database.get_job_by_id(job_id)
    if not job:
        flash('Job not found.', 'error')
        return redirect(url_for('jobs'))
    return render_template('job_detail.html', user=user, job=job)


# ==================== API ENDPOINTS ====================

@app.route('/api/stats')
@login_required
def api_stats():
    stats = database.get_queue_stats()
    return jsonify(dict(stats))


@app.route('/api/leaderboard')
def api_leaderboard():
    leaderboard = database.get_leaderboard(10)
    return jsonify([dict(row) for row in leaderboard])


@app.route('/api/cost', methods=['POST'])
@login_required
def api_calculate_cost():
    data = request.json or {}
    cost = database.calculate_job_cost(
        data.get('cpu', 1),
        data.get('ram', 1),
        data.get('gpu', 0),
        data.get('timeout', 300)
    )
    return jsonify({'cost': cost})


# ==================== FILE DOWNLOAD ====================

@app.route('/job/<job_id>/files')
@login_required
def job_files(job_id):
    """List all output files for a job"""
    job = database.get_job_by_id(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    output_dir = os.path.join(os.path.dirname(__file__), 'job_outputs', job_id)
    files = []

    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            filepath = os.path.join(output_dir, filename)
            if os.path.isfile(filepath):
                files.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'url': url_for('download_file', job_id=job_id, filename=filename)
                })

    return jsonify({'files': files})


@app.route('/job/<job_id>/download/<filename>')
@login_required
def download_file(job_id, filename):
    """Download a specific output file"""
    job = database.get_job_by_id(job_id)
    if not job:
        flash('Job not found.', 'error')
        return redirect(url_for('jobs'))

    output_dir = os.path.join(os.path.dirname(__file__), 'job_outputs', job_id)

    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        flash('Invalid filename.', 'error')
        return redirect(url_for('job_detail', job_id=job_id))

    filepath = os.path.join(output_dir, filename)
    if not os.path.exists(filepath):
        flash('File not found.', 'error')
        return redirect(url_for('job_detail', job_id=job_id))

    return send_from_directory(output_dir, filename, as_attachment=True)


# ==================== WORKER MANAGEMENT ====================

@app.route('/my-workers')
@login_required
def my_workers():
    """Show user's workers with controls"""
    user = get_current_user()
    workers_list = database.get_user_workers(user['id'])
    return render_template('my_workers.html', user=user, workers=workers_list)


@app.route('/worker/<worker_id>/pause', methods=['POST'])
@login_required
def pause_worker(worker_id):
    """Pause a worker"""
    user = get_current_user()
    worker = database.get_worker_by_id(worker_id)
    if not worker or (worker['owner_id'] != user['id'] and not user.get('is_admin')):
        flash('Worker not found or access denied.', 'error')
        return redirect(url_for('my_workers'))
    if database.pause_worker(worker_id):
        flash('Worker paused. It will not receive new jobs.', 'success')
    else:
        flash('Failed to pause worker.', 'error')
    return redirect(url_for('my_workers'))


@app.route('/worker/<worker_id>/resume', methods=['POST'])
@login_required
def resume_worker(worker_id):
    """Resume a worker"""
    user = get_current_user()
    worker = database.get_worker_by_id(worker_id)
    if not worker or (worker['owner_id'] != user['id'] and not user.get('is_admin')):
        flash('Worker not found or access denied.', 'error')
        return redirect(url_for('my_workers'))
    if database.resume_worker(worker_id):
        flash('Worker resumed. It will now receive jobs.', 'success')
    else:
        flash('Failed to resume worker.', 'error')
    return redirect(url_for('my_workers'))


@app.route('/worker/<worker_id>/remove', methods=['POST'])
@login_required
def remove_worker(worker_id):
    """Remove a worker"""
    user = get_current_user()
    worker = database.get_worker_by_id(worker_id)
    if not worker or (worker['owner_id'] != user['id'] and not user.get('is_admin')):
        flash('Worker not found or access denied.', 'error')
        return redirect(url_for('my_workers'))
    if database.remove_worker(worker_id):
        flash('Worker removed.', 'success')
    else:
        flash('Failed to remove worker.', 'error')
    return redirect(url_for('my_workers'))


@app.route('/coordinator/user/<user_id>/role', methods=['POST'])
@role_required('coordinator')
def change_user_role(user_id):
    """Change a user's role (coordinator only)"""
    new_role = request.form.get('role')
    if new_role in ['coordinator', 'worker', 'user']:
        if database.set_user_role(user_id, new_role):
            flash(f'User role changed to {new_role}.', 'success')
        else:
            flash('Failed to change user role.', 'error')
    else:
        flash('Invalid role specified.', 'error')
    return redirect(url_for('coordinator_dashboard'))


@app.route('/admin/clear-history', methods=['POST'])
@admin_required
def clear_history():
    """Clear all job history (admin only)"""
    database.clear_job_history()
    flash('Job history cleared.', 'success')
    return redirect(url_for('jobs'))


@app.route('/admin/clear-workers', methods=['POST'])
@admin_required
def clear_workers():
    """Clear all workers (admin only)"""
    database.clear_workers()
    flash('All workers cleared.', 'success')
    return redirect(url_for('workers'))


# ==================== WEBSOCKET EVENTS ====================

@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        emit('connected', {'status': 'ok'})


@socketio.on('request_stats')
def handle_request_stats():
    stats = database.get_queue_stats()
    emit('stats_update', dict(stats))


# ==================== TEMPLATE CONTEXT ====================

@app.context_processor
def utility_processor():
    def format_datetime(dt):
        if dt:
            return dt.strftime('%Y-%m-%d %H:%M')
        return 'N/A'
    return dict(format_datetime=format_datetime)


# ==================== MAIN ====================

def run_dashboard(host='0.0.0.0', port=5001, debug=True):
    """Run the dashboard server"""
    database.init_db()
    print(f"\n{'='*50}")
    print(f"  CampusGrid Dashboard")
    print(f"  http://{host}:{port}")
    print(f"{'='*50}\n")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_dashboard()
