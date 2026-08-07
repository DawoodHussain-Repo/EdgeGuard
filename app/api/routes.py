import time
import io
import base64
import asyncio
import cv2
import numpy as np
from typing import Optional
from fastapi import APIRouter, Body, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from app.core.schemas import TelemetryResponse, StreamStatus
from app.vision.pipeline import pipeline

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


def _process_image_upload_sync(file_bytes: bytes) -> dict:
    """Synchronous worker function executed in thread pool to prevent blocking ASGI event loop."""
    np_arr = np.frombuffer(file_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid image file format")

    h, w = frame.shape[:2]
    # Upscale low-res images to HD resolution for crystal clear rendering & better detection
    target_min_dim = 1200
    min_dim = min(h, w)
    if min_dim < target_min_dim:
        scale_factor = target_min_dim / float(min_dim)
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        h, w = new_h, new_w

    person_tracks, ppe_detections = pipeline.detector.process_frame(frame, is_static=True)
    worker_statuses, active_violations, summary = pipeline.rules_engine.evaluate_frame(
        person_tracks, ppe_detections, frame_width=w, frame_height=h
    )

    annotated = pipeline.annotator.draw_annotations(frame, worker_statuses, pipeline.fps)
    _, buffer = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
    encoded_img = base64.b64encode(buffer.tobytes()).decode('utf-8')

    return {
        "status": "success",
        "image_data": f"data:image/jpeg;base64,{encoded_img}",
        "summary": summary,
        "worker_statuses": [w.model_dump() for w in worker_statuses],
        "violations": [v.model_dump() for v in active_violations]
    }


@router.get("/stream")
async def video_stream():
    """HTTP multipart/x-mixed-replace MJPEG video stream endpoint."""
    return StreamingResponse(
        pipeline.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/telemetry", response_model=TelemetryResponse)
async def get_telemetry():
    """Real-Time Telemetry API returning active workers & compliance metrics."""
    return pipeline.get_latest_telemetry()





@router.get("/stats", response_model=StreamStatus)
async def get_stream_stats():
    """Return backend vision pipeline performance metrics and stream status."""
    telemetry = pipeline.get_latest_telemetry()
    return StreamStatus(
        stream_active=pipeline.is_running,
        source="Synthetic Demo Feed / RTSP Feed",
        fps=pipeline.fps,
        frame_width=pipeline.frame_width,
        frame_height=pipeline.frame_height,
        active_workers=telemetry.active_workers,
        total_violations=len(telemetry.violations)
    )


@router.get("/health")
async def health_check():
    """Microservice health check endpoint."""
    return {
        "status": "healthy",
        "service": "EdgeGuard-AI Pipeline",
        "pipeline_running": pipeline.is_running,
        "fps": pipeline.fps,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


@router.post("/analyze/upload")
async def analyze_uploaded_file(file: UploadFile = File(...)):
    """Non-blocking async endpoint for uploading image/video frames for offline PPE safety analysis."""
    try:
        contents = await file.read()
        res = await asyncio.to_thread(_process_image_upload_sync, contents)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing error: {str(e)}")


@router.post("/test/trigger-violation")
async def trigger_test_violation():
    """Testing helper: trigger simulated worker PPE violation for live UI demonstration."""
    return pipeline.trigger_mock_violation()


@router.post("/test/switch-source")
async def switch_video_source(source: Optional[str] = Body(None, embed=True)):
    """Testing helper: switch video source ('0' for webcam, None for Synthetic Demo, or RTSP URL)."""
    pipeline.set_video_source(source)
    return {"status": "success", "active_source": source or "Synthetic Demo"}
