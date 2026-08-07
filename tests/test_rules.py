from app.core.rules import box_containment_ratio, PPEComplianceEngine


def test_box_containment_ratio():
    inner = [2.0, 2.0, 8.0, 8.0]  # area 36
    outer = [0.0, 0.0, 10.0, 10.0]  # area 100
    ratio = box_containment_ratio(inner, outer)
    assert ratio == 1.0

    outside = [12.0, 12.0, 20.0, 20.0]
    assert box_containment_ratio(outside, outer) == 0.0


def test_ppe_compliance_engine():
    engine = PPEComplianceEngine()

    person_tracks = [
        {"track_id": 1, "bbox": [100.0, 100.0, 200.0, 300.0], "confidence": 0.9}
    ]
    ppe_detections = [
        {"class_name": "helmet", "bbox": [110.0, 105.0, 190.0, 150.0], "confidence": 0.95},
        {"class_name": "vest", "bbox": [105.0, 155.0, 195.0, 260.0], "confidence": 0.92},
        {"class_name": "goggles", "bbox": [120.0, 120.0, 180.0, 140.0], "confidence": 0.90}
    ]

    workers, violations, summary = engine.evaluate_frame(person_tracks, ppe_detections)
    assert len(workers) == 1
    assert workers[0].has_helmet is True
    assert workers[0].has_vest is True
    assert workers[0].has_goggles is True
    assert summary["active_workers"] == 1
