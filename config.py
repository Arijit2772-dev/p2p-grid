"""
P2P Campus Compute Network - Configuration
"""

import os

# ==================== SERVER CONFIGURATION ====================

# Manager Server (TCP Socket for workers)
MANAGER_HOST = os.getenv('MANAGER_HOST', '0.0.0.0')
MANAGER_PORT = int(os.getenv('MANAGER_PORT', 9999))

# Dashboard Server (HTTP/WebSocket)
DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', 5000))

# ==================== SECURITY ====================

# Secret key for Flask sessions (CHANGE IN PRODUCTION!)
SECRET_KEY = os.getenv('SECRET_KEY', 'campus-grid-secret-key-change-me')

# ==================== DATABASE ====================

# SQLite database path
DB_PATH = os.getenv('DB_PATH', 'manager/campus_compute.db')

# ==================== WORKER SETTINGS ====================

# Heartbeat timeout (seconds before marking worker offline)
HEARTBEAT_TIMEOUT = int(os.getenv('HEARTBEAT_TIMEOUT', 60))

# Maximum job timeout (seconds)
MAX_JOB_TIMEOUT = int(os.getenv('MAX_JOB_TIMEOUT', 3600))

# Default job timeout
DEFAULT_JOB_TIMEOUT = int(os.getenv('DEFAULT_JOB_TIMEOUT', 300))

# ==================== DOCKER SANDBOXING ====================

# Enable Docker sandboxing (if Docker is available)
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# Docker image for running jobs
DOCKER_IMAGE = os.getenv('DOCKER_IMAGE', 'python:3.11-slim')

# Memory limit per container
DOCKER_MEMORY_LIMIT = os.getenv('DOCKER_MEMORY_LIMIT', '512m')

# ==================== CREDITS ====================

# Starting credits for new users
STARTING_CREDITS = int(os.getenv('STARTING_CREDITS', 100))

# Minimum credit cost for a job
MIN_JOB_COST = int(os.getenv('MIN_JOB_COST', 5))

# ==================== LOGGING ====================

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


def print_config():
    """Print current configuration"""
    print("\n=== CampusGrid Configuration ===")
    print(f"Manager: {MANAGER_HOST}:{MANAGER_PORT}")
    print(f"Dashboard: {DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print(f"Database: {DB_PATH}")
    print(f"Docker Sandbox: {'Enabled' if USE_DOCKER else 'Disabled'}")
    print(f"Starting Credits: {STARTING_CREDITS}")
    print(f"Log Level: {LOG_LEVEL}")
    print("================================\n")


if __name__ == '__main__':
    print_config()
