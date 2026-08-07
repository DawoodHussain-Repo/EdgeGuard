# Architecture Context - EdgeGuard-AI

## Stack

| Layer | Technology | Role |
| ----- | ---------- | ---- |
| Computer Vision | Ultralytics YOLOv8 / YOLOv11 | Object detection (Person, Helmet, Vest) |
| Tracking Engine | ByteTrack | Multi-object tracking (Track ID assignment) |
| Image Processing | OpenCV (`opencv-python-headless`) | ROI polygon mask, spatial drawing engine, frame encoding |
| Backend Framework | FastAPI + Uvicorn | Asynchronous web framework, REST API & MJPEG streaming |
| Data & Validation | Pydantic v2 | Telemetry & config response schema validation |
| Concurrency | Python `threading` & `queue.Queue` | Thread-safe frame capture, inference loop & client streaming |
| Frontend UI | HTML5, Vanilla CSS3, JavaScript (ES6+) | Modern industrial dark-theme dashboard & live monitoring player |
| Deployment | Docker (`python:3.10-slim`) | Containerized edge deployment |

## System Boundaries

- `app/main.py`: Entrypoint for FastAPI app, route definitions (`/api/v1/stream`, `/api/v1/telemetry`, `/api/v1/roi`, `/api/v1/health`), static file serving.
- `app/vision.py`: Manages video stream sources, YOLO+ByteTrack inference loop, frame annotation, FPS calculation, and thread-safe frame queueing.
- `app/rules.py`: Spatial compliance calculations (IoU/overlap of Person vs Helmet/Vest), ROI boundary intersection, active worker tracking state management.
- `app/schemas.py`: Pydantic models for API responses, violation telemetry, stream status, and ROI coordinates.
- `app/static/`: Static assets for the web dashboard (index.html, styles.css, app.js).
- `weights/`: Holds model weight files (`ppe_yolov8n.pt`).

## Storage Model

- **In-Memory Telemetry State**: Telemetry metrics (active workers, compliant vs non-compliant, active violations, recent frame timestamps, FPS) are held in thread-safe memory buffers updated per frame.
- **Dynamic Config**: Active ROI polygon settings and confidence thresholds are stored in runtime state and configurable via REST endpoints.

## Auth and Access Model

- Microservice designed for edge deployment within local network or behind API gateways.
- CORS policy enabled for dashboard UI access.

## Invariants

1. **Non-Blocking Streaming**: The video streaming generator never blocks main ASGI event loop threads; frame rendering uses background queueing with automatic frame dropping under lag.
2. **Track ID Persistence**: Worker compliance state is bound to unique ByteTrack track IDs to prevent duplicate violation counting across consecutive frames.
3. **Graceful Fallback**: If hardware camera feed or custom model weights are unavailable, the vision engine gracefully falls back to synthetic test stream processing.
