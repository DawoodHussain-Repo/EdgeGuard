# EdgeGuard-AI: Low-Latency Worker Safety & PPE Tracking Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-orange.svg)](https://docs.ultralytics.com/)
[![ByteTrack](https://img.shields.io/badge/Tracking-ByteTrack-purple.svg)](https://github.com/ifzhang/ByteTrack)
[![Docker](https://img.shields.io/badge/Docker-Edge--Ready-blue.svg)](https://www.docker.com/)

**EdgeGuard-AI** is an edge-optimized computer vision microservice designed to perform real-time personnel monitoring, multi-object tracking, and safety compliance checks on live RTSP video feeds, webcams, or video files.

Built using **YOLOv8**, **ByteTrack**, **FastAPI**, and **Docker**, the platform tracks site personnel, detects mandatory Personal Protective Equipment (PPE) compliance (hard hats, safety vests), flags violations, and streams low-latency annotated video alongside live JSON telemetry endpoints.

---

## Technical Stack & Architecture

* **Computer Vision & Tracking:** Ultralytics YOLOv8 / YOLOv11 (Construction-PPE Dataset), ByteTrack (Multi-Object Tracking), OpenCV (Spatial ROI & Drawing Engine)
* **Backend Microservice:** FastAPI, Uvicorn, Asynchronous Streaming (`StreamingResponse`)
* **Data & Telemetry:** Pydantic v2, Python Threading / Queueing System
* **DevOps & Containerization:** Docker (`python:3.10-slim`), NVIDIA Container Toolkit (CUDA runtime compatible)

```
                       +---------------------------------------+
                       |           Video Stream Input          |
                       |  (RTSP / MP4 File / Webcam / Synthetic) |
                       +-------------------+-------------------+
                                           |
                                           v
                       +-------------------+-------------------+
                       |      YOLOv8 + ByteTrack Engine        |
                       | (Object Detection & Track ID Assign)  |
                       +-------------------+-------------------+
                                           |
                                           v
                       +-------------------+-------------------+
                       |     Spatial Rules & ROI Engine        |
                       | (PPE Inclusion & Hazard Zone Bounds)  |
                       +---------+-------------------+---------+
                                 |                   |
                                 v                   v
              +------------------+----+         +----+------------------+
              | MJPEG Video Generator |         |  Real-Time Telemetry  |
              |   (/api/v1/stream)    |         |  (/api/v1/telemetry)  |
              +------------------+----+         +----+------------------+
                                 |                   |
                                 +---------+---------+
                                           |
                                           v
                       +-------------------+-------------------+
                       |     Modern Industrial Dashboard UI    |
                       |        (http://localhost:8000)        |
                       +---------------------------------------+
```

---

## Core Features

1. **Multi-Object Spatial Tracking:** Uses ByteTrack to maintain consistent tracking IDs across frames for workers and PPE items, avoiding double-counting violations.
2. **Dynamic Zone / ROI Violation Engine:** Defines non-compliance bounding box intersections (e.g., `Person` detected without associated `Helmet` or `Vest` ID or entering a danger ROI polygon).
3. **Low-Latency Streaming Endpoint:** Serves a live `/api/v1/stream` endpoint rendering real-time annotated bounding boxes and violation overlays at 30+ FPS.
4. **Real-Time Analytics API:** Exposes a `/api/v1/telemetry` endpoint returning live counts of active personnel, total violations, and inference latency metrics.
5. **Interactive Web Monitoring Dashboard:** Integrated dark-mode command center UI for monitoring video streams, compliance percentages, active worker breakdown, and live alert feeds.
6. **Edge-Ready Docker Containerization:** Configured for lightweight multi-stage container builds compatible with edge hardware runtimes (NVIDIA Jetson, x86/ARM devices).

---

## Directory Structure

```text
edgeguard-ai/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization and routes
│   ├── vision.py            # YOLO + ByteTrack inference loop & frame generator
│   ├── rules.py             # PPE compliance and spatial collision logic
│   ├── schemas.py           # Pydantic models for telemetry responses
│   └── static/              # Dark mode web dashboard UI (HTML, CSS, JS)
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── weights/
│   ├── README.md
│   └── ppe_yolov8n.pt       # Pre-trained PPE detection model weights
├── context/                 # Architectural specifications & progress tracker
├── Dockerfile               # Production Docker file for edge/cloud deployment
├── requirements.txt         # Core dependencies
└── README.md
```

---

## Quickstart Guide

### 1. Prerequisites & Installation

Ensure you have **Python 3.10+** installed on your system.

```bash
git clone https://github.com/DawoodHussain-Repo/EdgeGuard.git
cd EdgeGuard

python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Dependencies (`requirements.txt`)

```text
ultralytics>=8.1.0
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
opencv-python-headless>=4.9.0.80
numpy>=1.26.0
pydantic>=2.6.0
```

### 3. Running the Service Locally

Download model weights or place your pre-trained `ppe_yolov8n.pt` into the `weights/` directory (optional: an adaptive demo pipeline runs out-of-the-box if weights are omitted), then start the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* **Interactive Web Dashboard:** Open `http://localhost:8000` in your browser.
* **Live Annotated Stream:** Visit `http://localhost:8000/api/v1/stream`.
* **Live Telemetry API:** Query `http://localhost:8000/api/v1/telemetry`.
* **API Documentation:** Interactive Swagger docs at `http://localhost:8000/docs`.

---

## Key API Endpoints

### `GET /api/v1/stream`
Returns an HTTP `multipart/x-mixed-replace` MJPEG stream of the annotated video feed with color-coded bounding boxes, track IDs, and ROI overlays.

### `GET /api/v1/telemetry`
Returns JSON data containing current frame statistics:

```json
{
  "timestamp": "2026-08-08T01:36:49Z",
  "active_workers": 4,
  "compliant_workers": 3,
  "non_compliant_workers": 1,
  "restricted_zone_violations": 1,
  "violations": [
    {
      "track_id": 12,
      "missing_gear": ["helmet"],
      "in_restricted_zone": false,
      "person_bbox": [180.5, 220.0, 270.5, 430.0],
      "severity": "HIGH",
      "timestamp": "2026-08-08T01:36:49Z"
    }
  ],
  "fps": 31.4,
  "latency_ms": 8.5
}
```

### `GET /api/v1/roi` & `POST /api/v1/roi`
Get or dynamically update restricted danger zone polygon coordinates.

### `GET /api/v1/health`
Health check endpoint verifying pipeline state.

---

## Docker Deployment

Build and run the edge container using Docker:

```bash
# Build Docker image
docker build -t edgeguard-ai:latest .

# Run container on port 8000
docker run -d --name edgeguard_container -p 8000:8000 edgeguard-ai:latest
```

---

## Remote Git Repository

* **Repository:** `https://github.com/DawoodHussain-Repo/EdgeGuard.git`
* **Branch:** `main`
