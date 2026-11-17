# Transify — Deployment & System Operations Guide

> **Document:** Production & Local Deployment Manual  
> **Deployment Targets:** Local Bare-Metal (Windows/macOS/Linux) & Docker Containerization  
> **Target Port:** `8000`  

---

## 1. System Prerequisites

### 1.1 Minimum Hardware Specifications
- **Processor:** Dual-Core 2.0 GHz Intel Core i3 / AMD Ryzen 3 or higher.
- **RAM:** Minimum 4 GB (8 GB recommended for simultaneous webcam and high-res Braille scans).
- **Storage:** At least 500 MB free disk space.
- **Peripherals:** Built-in or external USB webcam (720p or 1080p @ 30 FPS) and standard microphone.
- **GPU:** *None required.* All ML inference executes on CPU.

### 1.2 Operating System Compatibility
- **Windows:** Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **macOS:** macOS Monterey (12.0) or newer (Intel & Apple Silicon M1/M2/M3 native).
- **Linux:** Ubuntu 20.04 / 22.04 LTS, Debian 11+, Fedora 36+.

---

## 2. Bare-Metal Local Setup Guide

### Step 1: Clone or Extract the Project
```bash
git clone https://github.com/Abrarafick/transify.git
cd transify
```

### Step 2: Initialize Python Virtual Environment
We recommend Python 3.10, 3.11, 3.12, 3.13, or 3.14:
```bash
# On Windows
python -m venv venv
.\venv\Scripts\activate

# On macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Package Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Environment Variables Setup
Copy the sample configuration file to `.env`:
```bash
cp .env.example .env
```
Key configuration parameters in `.env`:
```ini
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=sqlite:///./data/transify.db
CONFIDENCE_THRESHOLD=0.98
MCP_RESOLVER_ENABLED=true
```

### Step 5: Launch the Application
Start the ASGI production server:
```bash
python run_server.py --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000`** in Google Chrome or Microsoft Edge.

---

## 3. Docker Container Deployment

The repository includes a production-ready, multi-stage `Dockerfile`.

### Step 1: Build Docker Image
```bash
docker build -t transify:latest .
```

### Step 2: Run Docker Container
```bash
docker run -d \
  -p 8000:8000 \
  --name transify-container \
  --restart unless-stopped \
  transify:latest
```

### Step 3: Verify Container Health
```bash
curl http://localhost:8000/api/health
```

---

## 4. Production Reverse Proxy Configuration (Nginx)

When deploying behind an Nginx reverse proxy with HTTPS SSL termination:

```nginx
server {
    listen 80;
    server_name transify.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name transify.example.com;

    ssl_certificate /etc/letsencrypt/live/transify.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/transify.example.com/privkey.pem;

    # Secure WebRTC Camera & Audio Permissions Policy
    add_header Permissions-Policy "camera=(self), microphone=(self)";

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 25M;
    }
}
```

---

## 5. Troubleshooting & FAQ

| Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| **"Microphone/Camera permission blocked"** | Browser security restriction on non-HTTPS origins. | Use `http://localhost:8000` or configure HTTPS SSL certificate. |
| **"Address already in use: 8000"** | Another process is holding port 8000. | Run `python run_server.py --port 8080` or kill the PID using port 8000. |
| **"Image Quality FAILED (Sharpness < 25.0)"** | Motion blur or camera out of focus. | Retake photo with steady hands and good directional sidelight. |
| **"Speech recognition unsupported"** | Browser lacks Web Speech API implementation. | Use modern Chromium-based browsers (Google Chrome or Microsoft Edge). |
