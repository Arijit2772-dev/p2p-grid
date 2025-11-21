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

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

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
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
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
        user_id = database.create_user(username, password_hash, email or None)

        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            flash(f'Welcome to CampusGrid, {username}! You received 100 credits to start.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Username already taken.', 'error')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ==================== MAIN ROUTES ====================

@app.route('/')
@login_required
def index():
    user = get_current_user()
    stats = database.get_queue_stats()
    leaderboard = database.get_leaderboard(10)
    recent_jobs = database.get_jobs_by_status(limit=10)
    workers = database.get_all_workers()

    return render_template('index.html',
                           user=user,
                           stats=stats,
                           leaderboard=leaderboard,
                           recent_jobs=recent_jobs,
                           workers=workers)


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
        cpu_required = int(request.form.get('cpu', 1))
        ram_required = float(request.form.get('ram', 1))
        gpu_required = int(request.form.get('gpu', 0))
        timeout = int(request.form.get('timeout', 300))
        priority = int(request.form.get('priority', 5))

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
    data = request.json
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
    from flask import send_from_directory

    job = database.get_job_by_id(job_id)
    if not job:
        flash('Job not found.', 'error')
        return redirect(url_for('jobs'))

    output_dir = os.path.join(os.path.dirname(__file__), 'job_outputs', job_id)

    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
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
    if database.remove_worker(worker_id):
        flash('Worker removed.', 'success')
    else:
        flash('Failed to remove worker.', 'error')
    return redirect(url_for('my_workers'))


@app.route('/admin/clear-history', methods=['POST'])
@login_required
def clear_history():
    """Clear all job history"""
    database.clear_job_history()
    flash('Job history cleared.', 'success')
    return redirect(url_for('jobs'))


@app.route('/admin/clear-workers', methods=['POST'])
@login_required
def clear_workers():
    """Clear all workers"""
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
