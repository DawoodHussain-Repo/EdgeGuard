import io
import cv2
import numpy as np
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "pipeline_running" in data


def test_telemetry_endpoint():
    response = client.get("/api/v1/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "active_workers" in data
    assert "fps" in data





def test_stats_endpoint():
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "stream_active" in data


def test_trigger_violation_endpoint():
    response = client.post("/api/v1/test/trigger-violation")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_upload_analysis_endpoint():
    # Create test image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:, :] = (50, 50, 50)
    _, buffer = cv2.imencode('.jpg', img)
    file_bytes = io.BytesIO(buffer.tobytes())

    response = client.post(
        "/api/v1/analyze/upload",
        files={"file": ("test.jpg", file_bytes, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "image_data" in data
    assert "summary" in data


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
