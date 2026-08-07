import numpy as np
from app.vision.synthetic import SyntheticGenerator
from app.vision.annotator import VisionAnnotator
from app.core.schemas import WorkerStatus


def test_synthetic_generator():
    synth = SyntheticGenerator(1280, 720)
    frame, person_tracks, ppe_detections = synth.step()
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (720, 1280, 3)
    assert len(person_tracks) > 0


def test_synthetic_mock_violation():
    synth = SyntheticGenerator(1280, 720)
    res = synth.trigger_mock_violation()
    assert res["status"] == "success"
    assert "triggered_worker_id" in res


def test_vision_annotator():
    annotator = VisionAnnotator(1280, 720)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    worker = WorkerStatus(
        track_id=1,
        bbox=[100, 100, 200, 300],
        has_helmet=True,
        has_vest=True,
        is_compliant=True
    )
    result = annotator.draw_annotations(frame, [worker], 30.0)
    assert isinstance(result, np.ndarray)
    assert result.shape == (720, 1280, 3)
