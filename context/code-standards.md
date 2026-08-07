# Code Standards - EdgeGuard-AI

## General

- Keep modules single-purpose: `vision.py` for pipeline & inference, `rules.py` for spatial logic, `schemas.py` for data models, `main.py` for API routes.
- Thread safety is mandatory: shared telemetry data and frame buffers must use thread locks or atomic updates.
- Zero silent failures: log exceptions cleanly with context.

## Python & Pydantic

- Require explicit type annotations for function parameters and return types.
- Use Pydantic v2 schemas for request validation and response models.
- Keep frame processing loops efficient: avoid unnecessary copies of heavy numpy arrays.

## Vision & OpenCV

- Frame dimensions and color space (BGR for OpenCV, RGB for web rendering where applicable) must be explicitly managed.
- ROI polygons are normalized or pixel-scaled relative to original frame dimensions.
- Standardize bounding box structures: `[x1, y1, x2, y2, track_id, class_id, confidence]`.

## FastAPI & Web API

- Standardized JSON responses for API endpoints.
- `/api/v1/stream` uses `StreamingResponse` with `multipart/x-mixed-replace; boundary=frame`.
- Non-blocking generators: stream generator reads from frame buffer queue with timeout.

## Styling & Web UI

- Modern Vanilla CSS using custom CSS properties defined in `ui-context.md`.
- Responsive flex and grid layouts.
- Vanilla JavaScript with fetch/polling/SSE for live dashboard state synchronization without heavy external bundlers.
