# CampusGrid - Deployment Guide

This guide will help you deploy CampusGrid to the cloud so anyone can access it for your project submission.

## 🚀 Recommended: Deploy to Railway (FREE, No Credit Card)

Railway is the easiest option - it's free for hobby projects and doesn't require a credit card.

### Step 1: Prepare Your GitHub Repository

1. **Push your code to GitHub** (if not already done):
   ```bash
   git add .
   git commit -m "Add deployment configuration"
   git push origin main
   ```

### Step 2: Deploy to Railway

1. **Go to Railway**: https://railway.app/
2. **Sign up** with your GitHub account (free)
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Choose your p2p-grid repository**
6. Railway will automatically detect the Dockerfile and deploy!

### Step 3: Configure Environment Variables (Optional)

In Railway dashboard:
- Click on your service
- Go to "Variables" tab
- Add (if needed):
  - `SECRET_KEY`: your-secret-key-here
  - `STARTING_CREDITS`: 100

### Step 4: Get Your Public URL

1. Go to "Settings" tab
2. Click "Generate Domain"
3. You'll get a URL like: `campusgrid-production.up.railway.app`
4. **Share this URL with your evaluators!**

---

## 🔷 Alternative: Deploy to Render (FREE)

Render is another free option with a generous free tier.

### Steps:

1. **Go to Render**: https://render.com/
2. **Sign up** with GitHub
3. **Click "New +"** → **"Web Service"**
4. **Connect your repository**
5. Configure:
   - **Environment**: Docker
   - **Plan**: Free
6. **Click "Create Web Service"**
7. Wait 5-10 minutes for build
8. Get your URL: `campusgrid.onrender.com`

---

## 🐳 Alternative: Deploy to Any VPS with Docker

If you have a VPS (AWS, DigitalOcean, etc.):

```bash
# SSH into your server
ssh user@your-server.com

# Clone repository
git clone https://github.com/yourusername/p2p-grid.git
cd p2p-grid

# Build Docker image
docker build -t campusgrid .

# Run container
docker run -d \
  -p 80:5001 \
  -p 9999:9999 \
  --name campusgrid \
  --restart unless-stopped \
  campusgrid

# Check if running
docker ps
```

Your site will be available at: `http://your-server-ip`

---

## 🧪 Test Locally with Docker First

Before deploying, test the Docker build locally:

```bash
# Build the image
docker build -t campusgrid-test .

# Run locally
docker run -p 5001:5001 -p 9999:9999 campusgrid-test

# Test at: http://localhost:5001
```

---

## 📋 What Gets Deployed

When deployed, your evaluators can:
- ✓ Access the dashboard from anywhere
- ✓ Register accounts and login
- ✓ Submit jobs (if workers are available)
- ✓ View the leaderboard
- ✓ See the system status

**Note**: For workers to connect remotely, they need the public URL and worker port (9999) to be exposed.

---

## 🎯 For Project Submission

**Include in your submission:**

1. **Public URL**: `https://your-app.railway.app` or `https://your-app.onrender.com`
2. **Demo Credentials**: Create a demo account and share:
   - Username: `demo`
   - Password: `demo123`
3. **Documentation**: Include this DEPLOYMENT.md in your submission

**Important**: Keep the server running during evaluation!

---

## 🔧 Troubleshooting

### Issue: "Application Error" on Railway/Render
- Check logs in the dashboard
- Ensure all dependencies in requirements.txt are correct
- Verify environment variables are set

### Issue: Workers can't connect
- The free tier may not expose TCP port 9999
- Workers may need to run locally on the same machine
- Consider documenting this limitation in your project report

### Issue: Database resets on deployment
- This is expected with SQLite on free hosting
- For persistence, upgrade to a paid plan with volume storage
- Or use PostgreSQL (available on Railway/Render free tier)

---

## 💡 Pro Tips

1. **Add a demo video**: Record a demo showing the system working
2. **Pre-populate data**: Add sample jobs/workers to showcase functionality
3. **Document limitations**: Be transparent about free tier constraints
4. **Keep it running**: Don't shut down during evaluation period

Good luck with your project submission! 🎓
