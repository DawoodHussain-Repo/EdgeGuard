import time
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.schemas import TelemetryResponse, ROIConfig, StreamStatus
from app.vision import pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start vision background pipeline on app startup and clean up on shutdown."""
    print("[EdgeGuard FastAPI] Initializing EdgeGuard-AI Service...")
    pipeline.start()
    yield
    print("[EdgeGuard FastAPI] Shutting down EdgeGuard-AI Service...")
    pipeline.stop()


app = FastAPI(
    title="EdgeGuard-AI",
    description="Low-Latency Worker Safety & PPE Tracking Pipeline Microservice",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for external dashboard consumption
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static folder exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the interactive web monitoring dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "service": "EdgeGuard-AI",
        "status": "Running",
        "docs": "/docs",
        "stream": "/api/v1/stream",
        "telemetry": "/api/v1/telemetry"
    })


@app.get("/api/v1/stream")
async def video_stream():
    """
    HTTP multipart/x-mixed-replace MJPEG video stream endpoint.
    Serves 30+ FPS real-time annotated video feed with bounding boxes,
    ByteTrack IDs, and spatial ROI compliance overlays.
    """
    return StreamingResponse(
        pipeline.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/v1/telemetry", response_model=TelemetryResponse)
async def get_telemetry():
    """
    Real-Time Telemetry API returning live statistics:
    - Active worker count
    - Compliant vs Non-compliant worker counts
    - Active safety violations list (missing helmet, vest, or in restricted zone)
    - Vision pipeline FPS & frame latency
    """
    return pipeline.get_latest_telemetry()


@app.get("/api/v1/roi", response_model=ROIConfig)
async def get_roi_config():
    """Get active spatial Region of Interest (Restricted Safety Zone) configuration."""
    return pipeline.get_roi_config()


@app.post("/api/v1/roi", response_model=ROIConfig)
async def update_roi_config(config: ROIConfig = Body(...)):
    """Dynamically update spatial Region of Interest polygon and safety zone labels."""
    pipeline.update_roi(config)
    return pipeline.get_roi_config()


@app.get("/api/v1/stats", response_model=StreamStatus)
async def get_stream_stats():
    """Return backend vision pipeline performance metrics and stream status."""
    telemetry = pipeline.get_latest_telemetry()
    uptime = time.time() - pipeline.start_time
    return StreamStatus(
        stream_active=pipeline.is_running,
        source="Synthetic Demo Feed / RTSP Feed",
        fps=pipeline.fps,
        frame_width=pipeline.frame_width,
        frame_height=pipeline.frame_height,
        active_workers=telemetry.active_workers,
        total_violations=len(telemetry.violations)
    )


@app.get("/api/v1/health")
async def health_check():
    """Microservice health check endpoint."""
    return {
        "status": "healthy",
        "service": "EdgeGuard-AI Pipeline",
        "pipeline_running": pipeline.is_running,
        "fps": pipeline.fps,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
