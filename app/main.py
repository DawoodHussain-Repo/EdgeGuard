import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.vision.pipeline import pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize background vision pipeline on startup and stop on shutdown."""
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve interactive monitoring web dashboard."""
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
