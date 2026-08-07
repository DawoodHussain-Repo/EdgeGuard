from app.core.schemas import (
    Violation, WorkerStatus, TelemetryResponse, StreamStatus
)


def test_violation_schema():
    v = Violation(
        track_id=1,
        missing_gear=["helmet"],
        person_bbox=[100.0, 100.0, 200.0, 300.0],
        severity="CRITICAL"
    )
    assert v.track_id == 1
    assert v.missing_gear == ["helmet"]
    assert v.severity == "CRITICAL"


def test_worker_status_schema():
    w = WorkerStatus(
        track_id=2,
        bbox=[50.0, 50.0, 150.0, 250.0],
        has_helmet=True,
        has_vest=False,
        has_goggles=True,
        is_compliant=False
    )
    assert w.track_id == 2
    assert w.has_helmet is True
    assert w.has_vest is False
    assert w.has_goggles is True
    assert w.is_compliant is False


def test_telemetry_response_schema():
    t = TelemetryResponse(
        active_workers=3,
        compliant_workers=2,
        non_compliant_workers=1,
        violations=[],
        fps=30.0,
        latency_ms=8.5
    )
    assert t.active_workers == 3
    assert t.compliant_workers == 2
    assert t.fps == 30.0
