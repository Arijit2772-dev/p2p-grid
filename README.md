# CampusGrid - P2P Compute Sharing Network

A decentralized peer-to-peer compute sharing platform for campus environments. Students can share their idle CPU/GPU resources and earn credits to run their own compute-intensive jobs like ML training, simulations, and rendering.

## 🎯 Live Demo

**Try CampusGrid now:** [https://p2p-grid.onrender.com](https://p2p-grid.onrender.com)

✨ **No installation required** - Just visit, register, and start using!
- Register and get 100 free credits
- Submit jobs and see results in real-time
- Explore the dashboard and leaderboard

> **Note:** First load may take 30-60 seconds as the server wakes up (free tier)

## Features

- **P2P Resource Sharing**: Pool compute resources across campus
- **Docker Sandboxing**: Secure job execution in isolated containers
- **Credit System**: Fair exchange - earn credits by contributing, spend them on jobs
- **Resource-Aware Scheduling**: Jobs matched to capable workers
- **Real-time Dashboard**: Monitor jobs, workers, and leaderboard
- **GPU Support**: Automatic detection and scheduling for GPU workloads
- **User Authentication**: Secure login and credit tracking
- **Cloud Deployment Ready**: Deploy to Railway, Render, or any cloud platform

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

## 🚀 Quick Start Guide

### Option 1: Use the Live Demo (Easiest)

1. **Visit the Dashboard**: [https://p2p-grid.onrender.com](https://p2p-grid.onrender.com)
2. **Register an Account**:
   - Click "Register"
   - Choose your role: User (submit jobs) or Worker (earn credits)
   - Get 100 free credits!
3. **Submit Your First Job**:
   - Click "Submit Job"
   - Paste Python code or use examples
   - Set CPU/RAM requirements
   - Click Submit!
4. **View Results**: Check job status and download outputs

### Option 2: Run Locally

#### 1. Install Dependencies

```bash
git clone https://github.com/Arijit2772-dev/p2p-grid.git
cd p2p-grid
pip install -r requirements.txt
```

#### 2. Start the Manager

```bash
python run_manager.py
```

This starts:
- TCP server on port **9999** (for workers)
- Web dashboard on **http://localhost:5001**

#### 3. Access Dashboard

Open **http://localhost:5001** in your browser and register!

#### 4. (Optional) Add Workers

On the same or different machines:

```bash
# Basic usage
python run_worker.py -m <manager_ip>

# With all options
python run_worker.py -m 192.168.1.100 -n "MyLaptop" -u "john_doe"
```

**Worker Options:**
- `-m, --manager`: Manager IP address
- `-n, --name`: Custom worker name
- `-u, --user`: Your username (to earn credits)
- `--no-docker`: Disable Docker sandboxing

### Option 3: Deploy Your Own Instance

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for step-by-step cloud deployment guides for:
- Railway (free, easiest)
- Render (free)
- Docker/VPS deployment

## 📖 How to Use CampusGrid

### For Job Submitters (Users)

1. **Register** with role "User"
2. **Get 100 starting credits** automatically
3. **Submit a job**:
   - Navigate to "Submit Job"
   - Write Python code or upload a script
   - Specify pip requirements (e.g., `numpy pandas`)
   - Set CPU, RAM, GPU needs
   - Set timeout
4. **Track progress** in "My Jobs"
5. **Download results** when complete

**Example Use Cases:**
- Train machine learning models
- Run data analysis pipelines
- Perform scientific simulations
- Execute batch processing tasks

### For Contributors (Workers)

1. **Register** with role "Worker"
2. **Run worker client** on your machine:
   ```bash
   python run_worker.py -m <dashboard_url> -u <your_username>
   ```
3. **Earn credits** for each job completed
4. **Monitor earnings** in worker dashboard
5. **Use earned credits** to submit your own jobs!

### For Administrators (Coordinators)

1. **Register** with role "Coordinator"
2. **View all system activity**:
   - All jobs across the network
   - All connected workers
   - System statistics
3. **Manage users and credits**
4. **Monitor system health**

## 💡 How It Works

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
- No network access (prevents data exfiltration)
- Memory limits (prevents resource abuse)
- CPU quotas (fair resource sharing)
- Read-only filesystem (system protection)

## 💻 Example Jobs

Try these examples by copying the code into the "Submit Job" form!

### 1. Simple Computation
```python
# Calculate sum of squares
result = sum(i**2 for i in range(1_000_000))
print(f"Result: {result}")
```
**Requirements:** None
**Resources:** 1 CPU, 1GB RAM
**Credits Cost:** ~8

### 2. ML Training (with dependencies)
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
**Requirements:** `numpy scikit-learn`
**Resources:** 2 CPU, 4GB RAM
**Credits Cost:** ~18

### 3. Matrix Operations
```python
import numpy as np

# Heavy matrix multiplication
A = np.random.rand(1000, 1000)
B = np.random.rand(1000, 1000)
C = np.dot(A, B)

print(f"Result shape: {C.shape}")
print(f"Sum: {C.sum():.2f}")
```
**Requirements:** `numpy`
**Resources:** 2 CPU, 2GB RAM
**Credits Cost:** ~14

### 4. Data Analysis
```python
import pandas as pd
import numpy as np

# Generate sample data
data = pd.DataFrame({
    'A': np.random.randn(1000),
    'B': np.random.randn(1000),
    'C': np.random.choice(['X', 'Y', 'Z'], 1000)
})

# Perform analysis
print("Statistics:")
print(data.describe())
print("\nGroup Analysis:")
print(data.groupby('C')[['A', 'B']].mean())
```
**Requirements:** `pandas numpy`
**Resources:** 1 CPU, 2GB RAM
**Credits Cost:** ~12

More examples available in `examples/` folder!

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

## 🎓 Use Cases

### Academic Research
- Run computational experiments
- Process large datasets
- Train ML models without expensive hardware
- Parallel simulations

### Student Projects
- Test algorithms at scale
- Benchmark performance
- Collaborative computing
- Learn distributed systems

### Campus Computing Pool
- Share GPU resources for deep learning
- Distribute rendering tasks
- Batch processing for research groups
- Resource optimization

## 🔧 Troubleshooting

### "No workers available"
- Workers need to be running for jobs to execute
- You can run a worker on your own machine while testing
- In production, encourage others to contribute workers

### Worker can't connect
- Check manager IP is correct
- Ensure port 9999 is open in firewall
- Verify manager is running

### Docker not working
- Install Docker Desktop and ensure it's running
- Use `--no-docker` flag for restricted mode (less secure)

### Job stuck in pending
- Check if any workers are online
- Verify workers meet job requirements (CPU/RAM/GPU)
- Check worker dashboard to see available resources

### Credits running low
- Run a worker to earn more credits
- Each completed job rewards the worker owner

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Cloud deployment guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system architecture
- **[examples/](examples/)** - Sample job scripts

## 🤝 Contributing

This is a campus project for P2P compute sharing. Contributions welcome!

Ideas for contributions:
- Add more example jobs
- Improve UI/UX
- Add job templates
- Enhanced monitoring
- Mobile app

## 📄 License

MIT License - Use freely for educational purposes.

## 🙏 Acknowledgments

Built for campus compute sharing and distributed systems education.

---

**Questions?** Open an issue on GitHub
**Want to contribute?** Fork and submit a PR
