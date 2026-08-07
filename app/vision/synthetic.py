import cv2
import numpy as np
from typing import List, Dict, Any, Tuple


class SyntheticGenerator:
    """High-performance synthetic demonstration stream generator with simulated worker agents."""

    def __init__(self, frame_width: int = 1280, frame_height: int = 720):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self._demo_workers = [
            {"id": 1, "x": 180.0, "y": 280.0, "vx": 1.2, "vy": 0.8, "has_helmet": True, "has_vest": True},
            {"id": 2, "x": 580.0, "y": 420.0, "vx": -1.5, "vy": 0.6, "has_helmet": False, "has_vest": True},
            {"id": 3, "x": 320.0, "y": 500.0, "vx": 0.9, "vy": -1.1, "has_helmet": True, "has_vest": False},
            {"id": 4, "x": 750.0, "y": 320.0, "vx": -0.8, "vy": -0.7, "has_helmet": True, "has_vest": True},
            {"id": 5, "x": 220.0, "y": 380.0, "vx": 1.4, "vy": -0.5, "has_helmet": False, "has_vest": False},
        ]

    def trigger_mock_violation(self) -> Dict[str, Any]:
        """Trigger simulated worker violation for live dashboard testing."""
        if self._demo_workers:
            import random
            target = random.choice(self._demo_workers)
            target["has_helmet"] = False
            target["has_vest"] = False
            target["x"] = 250.0
            target["y"] = 450.0
            return {"status": "success", "triggered_worker_id": target["id"]}
        return {"status": "error", "message": "Demo workers inactive"}

    def step(self) -> Tuple[np.ndarray, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generate next frame canvas and simulated detection track metadata."""
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        frame[:, :] = (15, 20, 28)

        # Draw grid lines
        for y in range(0, self.frame_height, 60):
            cv2.line(frame, (0, y), (self.frame_width, y), (25, 33, 44), 1)
        for x in range(0, self.frame_width, 80):
            cv2.line(frame, (x, 0), (x, self.frame_height), (25, 33, 44), 1)

        person_tracks = []
        ppe_detections = []

        for w in self._demo_workers:
            w["x"] += w["vx"]
            w["y"] += w["vy"]

            if w["x"] < 120 or w["x"] > self.frame_width - 200:
                w["vx"] *= -1.0
            if w["y"] < 200 or w["y"] > self.frame_height - 180:
                w["vy"] *= -1.0

            x1, y1 = w["x"], w["y"]
            x2, y2 = x1 + 90, y1 + 210
            bbox = [x1, y1, x2, y2]

            person_tracks.append({"track_id": w["id"], "bbox": bbox, "confidence": 0.94})

            if w["has_helmet"]:
                ppe_detections.append({"class_name": "helmet", "bbox": [x1 + 10, y1 + 5, x2 - 10, y1 + 50], "confidence": 0.92})
            if w["has_vest"]:
                ppe_detections.append({"class_name": "vest", "bbox": [x1 + 5, y1 + 55, x2 - 5, y2 - 40], "confidence": 0.89})

        return frame, person_tracks, ppe_detections
