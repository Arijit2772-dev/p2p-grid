# CampusGrid - P2P Compute Sharing Network

A decentralized peer-to-peer compute sharing platform for campus environments. Students can share their idle CPU/GPU resources and earn credits to run their own compute-intensive jobs like ML training, simulations, and rendering.

## Features

- **P2P Resource Sharing**: Pool compute resources across campus
- **Docker Sandboxing**: Secure job execution in isolated containers
- **Credit System**: Fair exchange - earn credits by contributing, spend them on jobs
- **Resource-Aware Scheduling**: Jobs matched to capable workers
- **Real-time Dashboard**: Monitor jobs, workers, and leaderboard
- **GPU Support**: Automatic detection and scheduling for GPU workloads
- **User Authentication**: Secure login and credit tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CampusGrid Network                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐     ┌──────────────┐                    │
│   │   Student A  │     │   Student B  │                    │
│   │   (Worker)   │     │   (Worker)   │                    │
│   │  ┌────────┐  │     │  ┌────────┐  │                    │
│   │  │ CPU/GPU│  │     │  │ CPU/GPU│  │                    │
│   │  └────────┘  │     │  └────────┘  │                    │
│   └──────┬───────┘     └──────┬───────┘                    │
│          │                    │                             │
│          └────────┬───────────┘                             │
│                   │                                         │
│          ┌────────▼────────┐                                │
│          │   Manager Node   │                               │
│          │  ┌────────────┐  │                               │
│          │  │ Job Queue  │  │                               │
│          │  │ Scheduler  │  │                               │
│          │  │ Dashboard  │  │                               │
│          │  └────────────┘  │                               │
│          └─────────────────┘                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd p2p
pip install -r requirements.txt
```

### 2. Start the Manager (on one machine)

```bash
python run_manager.py
```

This starts:
- TCP server on port **9999** (for workers)
- Web dashboard on **http://localhost:5000**

### 3. Start Workers (on other machines)

```bash
# Basic usage
python run_worker.py -m <manager_ip>

# With all options
python run_worker.py -m 192.168.1.100 -n "MyLaptop" -u "john_doe"
```

Options:
- `-m, --manager`: Manager IP address
- `-n, --name`: Custom worker name
- `-u, --user`: Your username (to earn credits)
- `--no-docker`: Disable Docker sandboxing

### 4. Submit Jobs

1. Open **http://localhost:5000** in your browser
2. Register/login
3. Click "Submit Job"
4. Enter your Python code
5. Set resource requirements
6. Submit!

## How It Works

### Credit System

| Action | Credits |
|--------|---------|
| New user signup | +100 |
| Complete a job (worker) | +job_cost |
| Submit a job | -calculated_cost |

**Job Cost Formula:**
```
cost = 5 (base) + 2×(cpu_cores) + 1×(ram_gb) + 10×(gpu) + 1×(minutes)
```

### Job Lifecycle

```
[Submitted] → [Pending] → [Running] → [Completed/Failed]
     │            │           │              │
     │            │           │              └─ Credits to worker
     │            │           └─ Assigned to matching worker
     │            └─ In queue, waiting for available worker
     └─ Credits deducted from submitter
```

### Security

Jobs run in Docker containers with:
- No network access
- Memory limits
- CPU quotas
- Read-only filesystem

## Example Jobs

### Simple Computation
```python
# Calculate sum of squares
result = sum(i**2 for i in range(1_000_000))
print(f"Result: {result}")
```

### ML Training (with dependencies)
```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

# Generate data
X, y = make_classification(n_samples=10000, n_features=20)

# Train model
clf = RandomForestClassifier(n_estimators=100)
clf.fit(X, y)

print(f"Accuracy: {clf.score(X, y):.4f}")
```

### Matrix Operations
```python
import numpy as np

# Heavy matrix multiplication
A = np.random.rand(1000, 1000)
B = np.random.rand(1000, 1000)
C = np.dot(A, B)

print(f"Result shape: {C.shape}")
print(f"Sum: {C.sum():.2f}")
```

## Directory Structure

```
p2p/
├── manager/
│   ├── server.py          # TCP server for workers
│   ├── dashboard.py       # Flask web dashboard
│   ├── database.py        # SQLite database operations
│   └── templates/         # HTML templates
│       ├── base.html
│       ├── index.html
│       ├── login.html
│       ├── register.html
│       ├── submit.html
│       ├── jobs.html
│       ├── my_jobs.html
│       ├── workers.html
│       └── job_detail.html
├── worker/
│   └── client.py          # Worker client with sandboxing
├── run_manager.py         # Manager startup script
├── run_worker.py          # Worker startup script
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
└── README.md
```

## Configuration

Set environment variables or edit `config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MANAGER_HOST` | 0.0.0.0 | Manager bind address |
| `MANAGER_PORT` | 9999 | Worker connection port |
| `DASHBOARD_PORT` | 5000 | Web dashboard port |
| `USE_DOCKER` | true | Enable Docker sandboxing |
| `STARTING_CREDITS` | 100 | Credits for new users |

## Troubleshooting

### Worker can't connect
- Check manager IP is correct
- Ensure port 9999 is open in firewall
- Verify manager is running

### Docker not working
- Install Docker and ensure it's running
- Use `--no-docker` flag for restricted mode

### Job stuck in pending
- Check if any workers are online
- Verify workers meet job requirements (CPU/RAM/GPU)

## Contributing

This is a campus project for P2P compute sharing. Contributions welcome!

## License

MIT License - Use freely for educational purposes.
