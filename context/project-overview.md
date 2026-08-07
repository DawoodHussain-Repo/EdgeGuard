# EdgeGuard-AI: Low-Latency Worker Safety & PPE Tracking Pipeline

## Overview

EdgeGuard-AI is an edge-optimized computer vision microservice designed to perform real-time personnel monitoring, multi-object tracking, and safety compliance checks on live RTSP video feeds, webcams, or video files. Built using YOLOv8/YOLOv11, ByteTrack, OpenCV, FastAPI, and Docker, the platform tracks site personnel, detects mandatory Personal Protective Equipment (PPE) compliance (hard hats, safety vests), flags violations, and streams low-latency annotated video alongside live JSON telemetry endpoints.

## Goals

1. **High-Speed Object Detection & Tracking**: Process video streams at 30+ FPS maintaining consistent tracking IDs across frames using ByteTrack.
2. **Spatial PPE Compliance & ROI Engine**: Accurately associate worker track IDs with protective equipment (helmets, vests) and detect missing gear and restricted zone violations without double-counting.
3. **Low-Latency Telemetry & Streaming**: Expose `/api/v1/stream` (MJPEG) and `/api/v1/telemetry` endpoints with minimal buffer delay (<50ms processing latency).

## Core User Flow

1. **Feed Ingestion**: Stream ingestion from RTSP camera, MP4 file, webcam, or synthetic demo generator.
2. **Frame Processing Loop**: Frame grabbing thread feeds frames into the Vision Pipeline.
3. **YOLO + ByteTrack Inference**: Bounding boxes, class predictions (Person, Helmet, Vest, No-Helmet, No-Vest), and track IDs are extracted.
4. **Spatial Rules Engine**: Checks spatial inclusion/IoU between Person bounding boxes and PPE objects, as well as dangerous ROI boundaries.
5. **Annotation Engine**: OpenCV draws track IDs, color-coded bounding boxes (Green = Compliant, Red = Violation, Amber = Warning), ROI zone overlays, and HUD statistics onto the frame.
6. **Broadcasting & Monitoring**: Frame is pushed to MJPEG stream queue; real-time JSON metrics are served on `/api/v1/telemetry`; interactive web dashboard displays live monitoring visualizer.

## Features

### Computer Vision & Object Tracking
- YOLOv8 / YOLOv11 detection engine tuned for Construction-PPE datasets.
- ByteTrack multi-object tracking algorithm for robust object association across occlusions and motion blur.
- Fallback synthetic video stream generation for reliable offline/standalone demonstration.

### Safety Rules & Spatial Analytics Engine
- Dynamic bounding box association between Person tracks and PPE items (Helmet, Vest).
- Dynamic ROI (Region of Interest) / Danger Zone collision detection.
- Real-time violation tracking per worker ID to prevent duplicate alerts.

### REST API & Live Streaming
- `GET /api/v1/stream`: HTTP `multipart/x-mixed-replace` MJPEG stream with dynamic annotations.
- `GET /api/v1/telemetry`: JSON metrics containing timestamp, active workers, compliant/non-compliant counts, active violations, and FPS.
- `GET /api/v1/roi` & `POST /api/v1/roi`: Dynamic ROI polygon configuration.
- `GET /api/v1/health`: Microservice health check & model readiness.

### Edge-Ready Architecture
- Lightweight container build (`python:3.10-slim`).
- NVIDIA Jetson and CUDA runtime compatible.

## Scope

### In Scope
- Real-time worker and PPE detection (helmet, vest).
- Multi-object tracking with ByteTrack ID assignment.
- Spatial ROI collision & compliance verification.
- FastAPI MJPEG video streaming & JSON telemetry API.
- Web-based industrial monitoring dashboard UI with interactive ROI customization.
- Dockerfile containerization.

### Out of Scope
- External cloud user authentication databases (managed locally / simple API).
- Video archival storage server (focus is on live microservice streaming and telemetry).

## Success Criteria

1. Streaming endpoint (`/api/v1/stream`) delivers continuous annotated frames at 30+ FPS.
2. Telemetry endpoint (`/api/v1/telemetry`) accurately reflects active worker counts, compliance metrics, and active violation details.
3. Web UI dashboard visualizes live feed, system performance, active worker breakdown, and violation alerts seamlessly.
4. Docker build compiles cleanly and runs microservice on port 8000.
