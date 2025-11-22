# CampusGrid P2P Compute Network - Architecture Guide

> A beginner-friendly guide to understanding how CampusGrid works

---

## Table of Contents
1. [What is CampusGrid?](#1-what-is-campusgrid)
2. [System Overview](#2-system-overview)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Core Components](#4-core-components)
5. [How Jobs Flow Through the System](#5-how-jobs-flow-through-the-system)
6. [Credit System](#6-credit-system)
7. [Communication Protocol](#7-communication-protocol)
8. [Database Schema](#8-database-schema)
9. [Security Model](#9-security-model)
10. [How to Run](#10-how-to-run)

---

## 1. What is CampusGrid?

CampusGrid is a **peer-to-peer compute sharing platform** designed for campus environments. Think of it like Airbnb, but for computing power:

- **Workers** = Students who share their computer's idle resources (like renting out a room)
- **Users** = Students who need computing power for their tasks (like booking a room)
- **Credits** = The currency used to pay for compute time

```
+------------------+       +------------------+       +------------------+
|   Student A      |       |   Student B      |       |   Student C      |
|   (Has GPU)      |       |   (Has 16 cores) |       |   (Needs compute)|
|                  |       |                  |       |                  |
|  Runs Worker     |       |  Runs Worker     |       |  Submits Jobs    |
|  Earns Credits   |       |  Earns Credits   |       |  Spends Credits  |
+------------------+       +------------------+       +------------------+
         |                         |                         |
         +-----------+-------------+-----------+-------------+
                     |                         |
                     v                         v
              +-------------------------------+
              |      CampusGrid Manager       |
              |   (Central Coordinator)       |
              +-------------------------------+
```

---

## 2. System Overview

### The Three Main Roles

| Role | What They Do | How They Benefit |
|------|--------------|------------------|
| **Coordinator** | Manages the system, views all jobs/workers | Full admin access |
| **Worker** | Contributes compute resources | Earns credits for each job completed |
| **User** | Submits compute jobs | Gets work done without local hardware |

### The Three Main Components

```
+-------------------------------------------------------------------+
|                        CampusGrid System                          |
+-------------------------------------------------------------------+
|                                                                   |
|  +------------------+  +------------------+  +------------------+ |
|  |                  |  |                  |  |                  | |
|  |  MANAGER SERVER  |  |    DASHBOARD     |  |  WORKER CLIENT   | |
|  |  (server.py)     |  |  (dashboard.py)  |  |   (client.py)    | |
|  |                  |  |                  |  |                  | |
|  |  - Job Queue     |  |  - Web UI        |  |  - Executes Jobs | |
|  |  - Scheduling    |  |  - Login/Register|  |  - Sends Results | |
|  |  - Worker Mgmt   |  |  - Job Submit    |  |  - Heartbeats    | |
|  |                  |  |                  |  |                  | |
|  |  Port: 9999      |  |  Port: 5001      |  |  Connects to Mgr | |
|  +------------------+  +------------------+  +------------------+ |
|           |                    |                     |            |
|           +--------------------+---------------------+            |
|                                |                                  |
|                    +-----------v-----------+                      |
|                    |      DATABASE         |                      |
|                    |   (SQLite .db file)   |                      |
|                    |                       |                      |
|                    |  - Users & Credits    |                      |
|                    |  - Jobs & Results     |                      |
|                    |  - Workers & Stats    |                      |
|                    +-----------------------+                      |
+-------------------------------------------------------------------+
```

---

## 3. Architecture Diagram

### High-Level Network View

```
                              INTERNET/CAMPUS NETWORK
    +=======================================================================+
    |                                                                       |
    |   +-------------+     +-------------+     +-------------+             |
    |   | Worker PC 1 |     | Worker PC 2 |     | Worker PC 3 |   ...       |
    |   | (Student A) |     | (Student B) |     | (Student C) |             |
    |   +------+------+     +------+------+     +------+------+             |
    |          |                   |                   |                    |
    |          |    TCP Socket     |    TCP Socket     |                    |
    |          |    Port 9999      |    Port 9999      |                    |
    |          |                   |                   |                    |
    |          +-------------------+-------------------+                    |
    |                              |                                        |
    |                              v                                        |
    |                    +------------------+                               |
    |                    |  MANAGER SERVER  |                               |
    |                    |                  |                               |
    |                    |  192.168.1.100   |                               |
    |                    |  Port: 9999      |<---- Workers connect here     |
    |                    |  Port: 5001      |<---- Web Dashboard here       |
    |                    +------------------+                               |
    |                              ^                                        |
    |                              |                                        |
    |                    HTTP (Browser)                                     |
    |                              |                                        |
    |   +-------------+     +-------------+     +-------------+             |
    |   |   Browser   |     |   Browser   |     |   Browser   |             |
    |   | (View Jobs) |     | (Submit Job)|     | (Dashboard) |             |
    |   +-------------+     +-------------+     +-------------+             |
    |                                                                       |
    +=======================================================================+
```

### Component Interaction Flow

```
+------------------------------------------------------------------------+
|                         JOB LIFECYCLE                                   |
+------------------------------------------------------------------------+

  USER                    MANAGER                    WORKER
    |                        |                          |
    |  1. Submit Job         |                          |
    |  (via Dashboard)       |                          |
    |----------------------->|                          |
    |                        |                          |
    |                        |  2. Queue Job            |
    |                        |  (Database)              |
    |                        |                          |
    |                        |                          |
    |                        |<-------------------------|
    |                        |  3. Request Job          |
    |                        |                          |
    |                        |------------------------->|
    |                        |  4. Send Job Details     |
    |                        |     (code, timeout)      |
    |                        |                          |
    |                        |                          |  5. Execute Code
    |                        |                          |     (in Docker)
    |                        |                          |
    |                        |<-------------------------|
    |                        |  6. Send Results         |
    |                        |     (output, files)      |
    |                        |                          |
    |                        |  7. Update Database      |
    |                        |  8. Credit Worker        |
    |                        |                          |
    |<-----------------------|                          |
    |  9. View Results       |                          |
    |  (via Dashboard)       |                          |
    |                        |                          |
```

---

## 4. Core Components

### 4.1 Manager Server (`manager/server.py`)

The **brain** of the system. It:
- Accepts connections from workers
- Maintains a job queue
- Matches jobs to available workers
- Tracks worker health via heartbeats

```
+------------------------------------------+
|            MANAGER SERVER                |
+------------------------------------------+
|                                          |
|  +----------------+  +----------------+  |
|  | WorkerManager  |  | JobScheduler   |  |
|  |                |  |                |  |
|  | - workers{}    |  | - get_next_job |  |
|  | - register()   |  | - assign_job() |  |
|  | - heartbeat()  |  | - complete()   |  |
|  | - disconnect() |  |                |  |
|  +----------------+  +----------------+  |
|                                          |
|  +------------------------------------+  |
|  |          Socket Server             |  |
|  |                                    |  |
|  |  - Listen on port 9999             |  |
|  |  - Accept worker connections       |  |
|  |  - Handle JSON messages            |  |
|  |  - Thread per worker               |  |
|  +------------------------------------+  |
|                                          |
+------------------------------------------+
```

**Key Data Structures:**

```python
# Workers dictionary (in memory)
workers = {
    "worker-uuid-123": {
        "name": "StudentA-Laptop",
        "ip": "192.168.1.50",
        "status": "online",      # online, busy, offline
        "cpu_cores": 8,
        "ram_gb": 16,
        "gpu_name": "RTX 3080",
        "last_heartbeat": datetime,
        "socket": <socket object>
    }
}
```

### 4.2 Dashboard (`manager/dashboard.py`)

The **face** of the system - a web interface built with Flask:

```
+------------------------------------------+
|              WEB DASHBOARD               |
|            (Flask + SocketIO)            |
+------------------------------------------+
|                                          |
|  ROUTES:                                 |
|  +------------------------------------+  |
|  | /login, /register  - Auth pages   |  |
|  | /dashboard         - Role redirect |  |
|  | /coordinator       - Admin view    |  |
|  | /worker-dashboard  - Worker view   |  |
|  | /user-dashboard    - User view     |  |
|  | /submit            - Submit jobs   |  |
|  | /jobs              - Browse jobs   |  |
|  | /workers           - View workers  |  |
|  +------------------------------------+  |
|                                          |
|  FEATURES:                               |
|  - Session-based authentication          |
|  - Role-based access control             |
|  - Real-time updates (WebSocket)         |
|  - File upload for job code              |
|                                          |
+------------------------------------------+
```

### 4.3 Worker Client (`worker/client.py`)

The **muscles** of the system - runs on contributor machines:

```
+------------------------------------------+
|             WORKER CLIENT                |
+------------------------------------------+
|                                          |
|  +----------------+  +----------------+  |
|  |  SystemInfo    |  | SandboxExecutor|  |
|  |                |  |                |  |
|  | - detect_cpu() |  | - Docker mode  |  |
|  | - detect_ram() |  | - Restricted   |  |
|  | - detect_gpu() |  | - timeout      |  |
|  | - has_docker() |  | - collect files|  |
|  +----------------+  +----------------+  |
|                                          |
|  +------------------------------------+  |
|  |          WorkerClient              |  |
|  |                                    |  |
|  |  Main Loop:                        |  |
|  |  1. Connect to manager             |  |
|  |  2. Register with specs            |  |
|  |  3. Request job                    |  |
|  |  4. Execute job                    |  |
|  |  5. Send results                   |  |
|  |  6. Repeat from step 3             |  |
|  |                                    |  |
|  |  Background:                       |  |
|  |  - Send heartbeat every 30s        |  |
|  +------------------------------------+  |
|                                          |
+------------------------------------------+
```

**Execution Modes:**

```
+------------------------+     +------------------------+
|     DOCKER MODE        |     |   RESTRICTED MODE      |
|     (Preferred)        |     |   (Fallback)           |
+------------------------+     +------------------------+
|                        |     |                        |
|  - Full isolation      |     |  - Direct subprocess   |
|  - No network access   |     |  - Less secure         |
|  - Memory limits       |     |  - Faster startup      |
|  - CPU quotas          |     |  - No Docker needed    |
|  - Separate filesystem |     |                        |
|                        |     |                        |
+------------------------+     +------------------------+
```

---

## 5. How Jobs Flow Through the System

### Step-by-Step Job Flow

```
+=======================================================================+
|                          JOB FLOW DIAGRAM                             |
+=======================================================================+

STEP 1: USER SUBMITS JOB
+------------------------------------------------------------------+
|  User fills form:                                                 |
|  - Title: "Train ML Model"                                        |
|  - Code: import tensorflow as tf; model.fit(...)                 |
|  - CPU: 4 cores                                                   |
|  - RAM: 8 GB                                                      |
|  - GPU: Yes                                                       |
|  - Timeout: 10 minutes                                            |
+------------------------------------------------------------------+
                              |
                              v
STEP 2: COST CALCULATION
+------------------------------------------------------------------+
|  cost = 5 (base)                                                  |
|       + 2 * 4 (cpu)      = 8                                      |
|       + 1 * 8 (ram)      = 8                                      |
|       + 10 * 1 (gpu)     = 10                                     |
|       + 10 (timeout/60)  = 10                                     |
|  --------------------------                                       |
|  TOTAL COST: 41 credits                                           |
+------------------------------------------------------------------+
                              |
                              v
STEP 3: CREDIT CHECK & DEDUCTION
+------------------------------------------------------------------+
|  User has: 100 credits                                            |
|  Job costs: 41 credits                                            |
|  100 >= 41? YES -> Proceed                                        |
|  User now has: 59 credits (100 - 41)                              |
+------------------------------------------------------------------+
                              |
                              v
STEP 4: JOB QUEUED
+------------------------------------------------------------------+
|  INSERT INTO jobs (status='pending', ...)                         |
|  INSERT INTO job_queue (priority=5, queued_at=NOW())              |
+------------------------------------------------------------------+
                              |
                              v
STEP 5: WORKER REQUESTS JOB
+------------------------------------------------------------------+
|  Worker A: cpu=8, ram=16GB, gpu="RTX 3090"                        |
|  Worker sends: {"type": "request_job", "worker_id": "xxx"}        |
|                                                                   |
|  Manager checks:                                                  |
|  - Job needs: cpu=4, ram=8, gpu=yes                               |
|  - Worker has: cpu=8, ram=16, gpu=yes                             |
|  - 8 >= 4? YES                                                    |
|  - 16 >= 8? YES                                                   |
|  - has GPU? YES                                                   |
|  -> MATCH! Assign job to Worker A                                 |
+------------------------------------------------------------------+
                              |
                              v
STEP 6: JOB SENT TO WORKER
+------------------------------------------------------------------+
|  Manager sends:                                                   |
|  {                                                                |
|    "type": "job",                                                 |
|    "job_id": "abc-123",                                           |
|    "code": "import tensorflow as tf; ...",                        |
|    "requirements": "tensorflow>=2.0",                             |
|    "timeout": 600,                                                |
|    "credit_reward": 41                                            |
|  }                                                                |
+------------------------------------------------------------------+
                              |
                              v
STEP 7: WORKER EXECUTES JOB
+------------------------------------------------------------------+
|  Docker container created:                                        |
|  - Image: python:3.11-slim                                        |
|  - Network: disabled                                              |
|  - Memory: 1GB limit                                              |
|  - Code mounted at /app/job.py                                    |
|                                                                   |
|  Runs: pip install tensorflow && python /app/job.py               |
|  Captures: stdout, stderr, output files                           |
+------------------------------------------------------------------+
                              |
                              v
STEP 8: RESULTS SENT BACK
+------------------------------------------------------------------+
|  Worker sends:                                                    |
|  {                                                                |
|    "type": "job_result",                                          |
|    "job_id": "abc-123",                                           |
|    "success": true,                                               |
|    "output": "Training complete! Accuracy: 95%",                  |
|    "error": null,                                                 |
|    "files": [{"filename": "model.h5", "content": "base64..."}]    |
|  }                                                                |
+------------------------------------------------------------------+
                              |
                              v
STEP 9: CREDITS AWARDED
+------------------------------------------------------------------+
|  Worker A's owner receives: 41 credits                            |
|  Job status: 'completed'                                          |
|  Files saved to: /manager/job_outputs/abc-123/                    |
+------------------------------------------------------------------+
                              |
                              v
STEP 10: USER VIEWS RESULTS
+------------------------------------------------------------------+
|  User sees on dashboard:                                          |
|  - Status: Completed                                              |
|  - Output: "Training complete! Accuracy: 95%"                     |
|  - Downloads: model.h5                                            |
+------------------------------------------------------------------+
```

---

## 6. Credit System

### How Credits Work

```
+------------------------------------------------------------------+
|                      CREDIT ECONOMY                               |
+------------------------------------------------------------------+

  NEW USER                    JOB SUBMITTER              WORKER OWNER
  +--------+                  +------------+             +------------+
  |        |                  |            |             |            |
  | +100   |                  | -cost      |             | +reward    |
  | credits|                  | (submit)   |             | (complete) |
  |        |                  |            |             |            |
  +--------+                  +------------+             +------------+
      ^                            |                          ^
      |                            |                          |
  Registration                 Deducted                   Credited
                              immediately                on success


CREDIT FORMULA:
+------------------------------------------------------------------+
|  cost = 5                    (base fee)                           |
|       + 2 * cpu_cores        (CPU cost)                           |
|       + 1 * ram_gb           (Memory cost)                        |
|       + 10 * gpu             (GPU premium: 0 or 10)               |
|       + timeout_seconds / 60 (Time cost)                          |
+------------------------------------------------------------------+

EXAMPLES:
+------------------------------------------------------------------+
| Simple job (1 CPU, 1GB RAM, no GPU, 5 min):                       |
|   5 + 2*1 + 1*1 + 10*0 + 300/60 = 5 + 2 + 1 + 0 + 5 = 13 credits |
|                                                                   |
| Heavy job (8 CPU, 16GB RAM, GPU, 30 min):                         |
|   5 + 2*8 + 1*16 + 10*1 + 1800/60 = 5 + 16 + 16 + 10 + 30 = 77   |
+------------------------------------------------------------------+
```

### Credit Transaction Types

```
+------------------+--------+------------------------------------------+
| Transaction Type | Amount | When                                     |
+------------------+--------+------------------------------------------+
| user_registered  | +100   | New account created                      |
| job_submitted    | -cost  | User submits a job                       |
| job_completed    | +reward| Worker completes job successfully        |
| legacy_reward    | +n     | Admin manually adds credits              |
+------------------+--------+------------------------------------------+
```

---

## 7. Communication Protocol

### Message Format

```
+------------------------------------------------------------------+
|                    SOCKET MESSAGE FORMAT                          |
+------------------------------------------------------------------+

  +----------+--------------------------------------------------+
  | HEADER   |                    BODY                          |
  | (10 bytes)|               (JSON payload)                     |
  +----------+--------------------------------------------------+

  Example:
  "0000000156{"type":"register","name":"MyPC","specs":{...}}"

  - Header: "0000000156" = message is 156 bytes
  - Body: JSON object with message content
```

### Message Types

```
WORKER -> MANAGER:
+------------------------------------------------------------------+
| Type         | Purpose                      | Example Payload     |
+------------------------------------------------------------------+
| register     | Initial connection           | name, specs, token  |
| heartbeat    | Keep-alive signal            | worker_id, status   |
| request_job  | Ask for work                 | worker_id           |
| job_result   | Submit completed work        | job_id, output      |
| disconnect   | Graceful shutdown            | -                   |
+------------------------------------------------------------------+

MANAGER -> WORKER:
+------------------------------------------------------------------+
| Type         | Purpose                      | Example Payload     |
+------------------------------------------------------------------+
| registered   | Confirm registration         | worker_id, message  |
| job          | Send job to execute          | job_id, code        |
| no_job       | No pending jobs              | -                   |
| job_received | Acknowledge result           | job_id              |
+------------------------------------------------------------------+
```

### Connection Lifecycle

```
     WORKER                                    MANAGER
        |                                         |
        |  -------- TCP CONNECT --------->        |
        |                                         |
        |  -------- register ------------>        |
        |  <------- registered -----------        |
        |                                         |
        |  ======= MAIN LOOP START =======        |
        |                                         |
        |  -------- request_job --------->        |
        |  <------- job ------------------        |
        |                                         |
        |     [Execute code locally]              |
        |                                         |
        |  -------- job_result ---------->        |
        |  <------- job_received ---------        |
        |                                         |
        |  ======= LOOP CONTINUES ========        |
        |                                         |
        |  -------- heartbeat ----------->        | (every 30s)
        |                                         |
        |  -------- disconnect ---------->        | (on shutdown)
        |                                         |
```

---

## 8. Database Schema

### Entity Relationship Diagram

```
+------------------------------------------------------------------+
|                    DATABASE SCHEMA (SQLite)                       |
+------------------------------------------------------------------+

  +----------------+       +----------------+       +----------------+
  |     USERS      |       |     JOBS       |       |    WORKERS     |
  +----------------+       +----------------+       +----------------+
  | id (PK)        |<------| submitter_id   |       | id (PK)        |
  | username       |       | id (PK)        |------>| owner_id       |----+
  | password_hash  |       | title          |       | name           |    |
  | email          |       | code           |       | ip_address     |    |
  | credits        |       | requirements   |       | status         |    |
  | role           |       | status         |       | cpu_cores      |    |
  | is_admin       |       | cpu_required   |       | ram_gb         |    |
  | created_at     |       | ram_required   |       | gpu_name       |    |
  +----------------+       | gpu_required   |       | has_docker     |    |
         |                 | timeout        |       | total_jobs     |    |
         |                 | credit_cost    |       | total_credits  |    |
         |                 | worker_id      |------>+----------------+    |
         |                 | result_output  |                             |
         |                 | error_log      |                             |
         |                 +----------------+                             |
         |                        |                                       |
         |                        v                                       |
         |                 +----------------+                             |
         |                 |   JOB_QUEUE    |                             |
         |                 +----------------+                             |
         |                 | job_id (FK)    |                             |
         |                 | priority       |                             |
         |                 | queued_at      |                             |
         |                 +----------------+                             |
         |                                                                |
         v                                                                |
  +--------------------+                                                  |
  | CREDIT_TRANSACTIONS|                                                  |
  +--------------------+                                                  |
  | id (PK)            |                                                  |
  | user_id (FK)       |<-------------------------------------------------+
  | amount             |
  | transaction_type   |
  | job_id (FK)        |
  | description        |
  | created_at         |
  +--------------------+
```

### Key Tables

```sql
-- USERS: Account information
CREATE TABLE users (
    id TEXT PRIMARY KEY,           -- UUID
    username TEXT UNIQUE,          -- Login name
    password_hash TEXT,            -- bcrypt hash
    email TEXT,                    -- Optional email
    credits INTEGER DEFAULT 100,   -- Current balance
    role TEXT,                     -- 'coordinator', 'worker', 'user'
    is_admin INTEGER DEFAULT 0,    -- 1 if admin
    created_at DATETIME
);

-- WORKERS: Connected compute nodes
CREATE TABLE workers (
    id TEXT PRIMARY KEY,           -- UUID assigned by manager
    name TEXT,                     -- Friendly name
    owner_id TEXT,                 -- Who owns this worker (FK users.id)
    status TEXT,                   -- 'online', 'offline', 'busy'
    cpu_cores INTEGER,             -- Available CPU cores
    ram_gb REAL,                   -- Available RAM
    gpu_name TEXT,                 -- GPU model or NULL
    has_docker INTEGER,            -- 1 if Docker available
    total_jobs_completed INTEGER,  -- Lifetime counter
    total_credits_earned INTEGER   -- Lifetime earnings
);

-- JOBS: Submitted compute tasks
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,           -- UUID
    title TEXT,                    -- Job name
    submitter_id TEXT,             -- Who submitted (FK users.id)
    worker_id TEXT,                -- Who executed (FK workers.id)
    status TEXT,                   -- 'pending', 'running', 'completed', 'failed'
    code TEXT,                     -- Python code to execute
    requirements TEXT,             -- pip packages needed
    cpu_required INTEGER,          -- Minimum CPU cores
    ram_required_gb REAL,          -- Minimum RAM
    gpu_required INTEGER,          -- 1 if GPU needed
    timeout_seconds INTEGER,       -- Max execution time
    credit_cost INTEGER,           -- What user paid
    credit_reward INTEGER,         -- What worker earns
    result_output TEXT,            -- stdout from execution
    error_log TEXT                 -- stderr from execution
);
```

---

## 9. Security Model

### Job Isolation (Docker Sandbox)

```
+------------------------------------------------------------------+
|                    DOCKER SANDBOX                                 |
+------------------------------------------------------------------+

  HOST MACHINE                    DOCKER CONTAINER
  +------------------------+      +------------------------+
  |                        |      |                        |
  |  - Full network       |      |  - NO network access   |
  |  - All files          |      |  - Only /app, /output  |
  |  - Unlimited memory   |      |  - 1GB memory limit    |
  |  - All processes      |      |  - 200 process limit   |
  |                        |      |                        |
  +------------------------+      +------------------------+
          |                               ^
          |        ISOLATION WALL         |
          +-------------------------------+

  What malicious code CANNOT do:
  - Access the internet (exfiltrate data)
  - Read host files (steal data)
  - Fork bomb (crash the system)
  - Use unlimited memory (DoS attack)
```

### Authentication & Authorization

```
+------------------------------------------------------------------+
|                 ROLE-BASED ACCESS CONTROL                         |
+------------------------------------------------------------------+

  COORDINATOR (Admin)
  +----------------------------------------------------------+
  | - View all jobs, workers, users                           |
  | - Change user roles                                       |
  | - Clear job history                                       |
  | - Access coordinator dashboard                            |
  +----------------------------------------------------------+

  WORKER (Contributor)
  +----------------------------------------------------------+
  | - View own workers                                        |
  | - Pause/resume/remove own workers                         |
  | - View earnings and stats                                 |
  | - Access worker dashboard                                 |
  +----------------------------------------------------------+

  USER (Consumer)
  +----------------------------------------------------------+
  | - Submit jobs                                             |
  | - View own jobs and results                               |
  | - Download output files                                   |
  | - Access user dashboard                                   |
  +----------------------------------------------------------+
```

---

## 10. How to Run

### Starting the Manager

```bash
# Terminal 1: Start the manager
cd /Users/arijitsingh/Desktop/p2p
python3 run_manager.py

# Output:
# ==========================================
#   CampusGrid Manager
# ==========================================
#   YOUR NETWORK IP: 192.168.1.100
#
#   Workers connect to: 192.168.1.100:9999
#   Dashboard: http://localhost:5001
# ==========================================
```

### Starting a Worker

```bash
# Terminal 2: Start a worker (on same or different machine)
cd /Users/arijitsingh/Desktop/p2p
python3 run_worker.py -m 192.168.1.100 -n "MyLaptop" -u "myusername"

# Arguments:
#   -m : Manager IP address
#   -n : Worker name (friendly identifier)
#   -u : Username (owner of the worker)
```

### Accessing the Dashboard

```
Open browser: http://localhost:5001

1. Register a new account
2. Choose your role (coordinator, worker, or user)
3. Start submitting jobs or contributing resources!
```

### Network Diagram for Multi-Machine Setup

```
+------------------------------------------------------------------+
|                    NETWORK SETUP EXAMPLE                          |
+------------------------------------------------------------------+

  MANAGER MACHINE (Your Mac)
  IP: 192.168.1.100
  +---------------------------+
  |  run_manager.py           |
  |                           |
  |  Ports:                   |
  |  - 9999 (worker socket)   |
  |  - 5001 (web dashboard)   |
  +---------------------------+
              |
    +---------+---------+
    |                   |
    v                   v
  WORKER 1            WORKER 2
  IP: 192.168.1.101   IP: 192.168.1.102
  +---------------+   +---------------+
  | run_worker.py |   | run_worker.py |
  | -m 192.168... |   | -m 192.168... |
  +---------------+   +---------------+


  IMPORTANT: All machines must be on the same network!
  If using campus WiFi with "client isolation", use:
  - Mobile hotspot
  - Ethernet connection
  - VPN tunnel (ngrok, cloudflared)
```

---

## Quick Reference

### File Structure

```
/Users/arijitsingh/Desktop/p2p/
├── manager/
│   ├── server.py          # TCP server for workers
│   ├── database.py        # SQLite operations
│   ├── dashboard.py       # Flask web UI
│   ├── campus_compute.db  # Database file
│   └── templates/         # HTML templates
├── worker/
│   └── client.py          # Worker client code
├── run_manager.py         # Start manager
├── run_worker.py          # Start worker
├── config.py              # Configuration
└── examples/              # Sample job scripts
```

### Common Commands

```bash
# Start manager
python3 run_manager.py

# Start worker
python3 run_worker.py -m <MANAGER_IP> -n "WorkerName" -u "username"

# Check if port is in use
lsof -i :5001
lsof -i :9999

# Kill all Python processes
pkill -f "python3"
```

---

## Summary

CampusGrid is a **3-tier architecture**:

1. **Presentation Layer**: Flask Dashboard (Web UI)
2. **Application Layer**: Manager Server (Job scheduling, worker management)
3. **Data Layer**: SQLite Database (Persistent storage)

Workers connect via **TCP sockets**, execute jobs in **Docker containers**, and earn **credits** for their contributions. Users submit jobs via the **web dashboard** and pay with credits.

The system is designed for **campus-scale** deployments (100-1000 users) with a focus on **simplicity** and **security**.
