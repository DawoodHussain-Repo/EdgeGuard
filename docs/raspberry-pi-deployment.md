# Raspberry Pi 4/5 Deployment Guide - EdgeGuard-AI

This guide provides step-by-step instructions for deploying EdgeGuard-AI on edge devices such as **Raspberry Pi 4 (4GB/8GB)** and **Raspberry Pi 5** operating on 64-bit ARM64 OS.

---

## 1. Prerequisites & Hardware Setup

### Recommended Hardware
- **Raspberry Pi 4 (4GB or 8GB)** or **Raspberry Pi 5**.
- **64-bit OS**: Raspberry Pi OS 64-bit (Debian Bookworm) or Ubuntu 22.04 LTS ARM64.
- **Storage**: High-speed MicroSD card (UHS-I A2) or NVMe SSD HAT.
- **Camera Input**: USB Webcam (`/dev/video0`), Raspberry Pi Camera Module 3 (CSI), or IP RTSP Camera.

### Install Base Packages
```bash
sudo apt-get update && sudo apt-get install -y \
    python3-pip \
    python3-venv \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    curl \
    git
```

---

## 2. Docker Container Deployment (Recommended)

Docker provides an isolated, production-grade environment optimized for ARM64 edge architectures.

### Step 2.1: Install Docker Engine & Buildx
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2.2: Clone & Build EdgeGuard-AI Container
```bash
git clone https://github.com/DawoodHussain-Repo/EdgeGuard.git
cd EdgeGuard

# Build ARM64 container
docker build -t edgeguard:rpi .
```

### Step 2.3: Run Container with Camera Access
```bash
# For USB Camera (/dev/video0)
docker run -d \
  --name edgeguard-pi \
  --restart unless-stopped \
  --device=/dev/video0:/dev/video0 \
  -p 8000:8000 \
  edgeguard:rpi

# Verification
curl http://localhost:8000/api/v1/health
```

---

## 3. Native Systemd Service Setup

If running directly on host Python virtual environment:

### Step 3.1: Initialize Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.2: Create Systemd Service File
Create `/etc/systemd/system/edgeguard.service`:
```ini
[Unit]
Description=EdgeGuard-AI Safety Telemetry Service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/EdgeGuard
ExecStart=/home/pi/EdgeGuard/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Step 3.3: Enable & Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable edgeguard
sudo systemctl start edgeguard
```

---

## 4. Input Video Source Configuration

Switch video sources dynamically via HTTP POST API:

```bash
# Switch to USB Webcam (/dev/video0)
curl -X POST http://localhost:8000/api/v1/test/switch-source \
  -H "Content-Type: application/json" \
  -d '{"source": "0"}'

# Switch to RTSP IP Camera stream
curl -X POST http://localhost:8000/api/v1/test/switch-source \
  -H "Content-Type: application/json" \
  -d '{"source": "rtsp://admin:pass@192.168.1.100:554/stream1"}'

# Revert to Synthetic High-Framerate Test Feed
curl -X POST http://localhost:8000/api/v1/test/switch-source \
  -H "Content-Type: application/json" \
  -d '{"source": null}'
```

---

## 5. Raspberry Pi Performance Tuning Tips

1. **Resolution Downscaling**: Set frame processing dimensions to `640x360` or `1280x720` in `app/vision/pipeline.py` for optimal FPS on Pi 4.
2. **ONNX Export**: Convert YOLO model to ONNX runtime format (`yolov8n.onnx`) for 2x faster inference on ARM CPU cores:
   ```python
   from ultralytics import YOLO
   model = YOLO("weights/ppe_yolov8n.pt")
   model.export(format="onnx", imgsz=640)
   ```
3. **Headless OpenCV**: Use `opencv-python-headless` as included in `requirements.txt` to save GUI overhead.
