import os
from typing import Optional, List, Dict, Any, Tuple
import numpy as np

try:
    from ultralytics import YOLO, YOLOWorld
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


class VisionDetector:
    """YOLOv8/YOLOv11 and YOLO-World Zero-Shot model detector manager."""

    def __init__(self, model_path: Optional[str] = "weights/ppe_yolov8n.pt"):
        self.model = None
        self.is_yolo_world = False
        self._init_model(model_path)

    def _init_model(self, model_path: Optional[str]):
        if not ULTRALYTICS_AVAILABLE:
            return

        if model_path and os.path.exists(model_path):
            try:
                self.model = YOLO(model_path)
                print(f"[EdgeGuard Vision] Loaded custom PPE YOLO model: {model_path}")
            except Exception as e:
                print(f"[EdgeGuard Vision] Custom model load error ({e}).")

        if self.model is None:
            try:
                print("[EdgeGuard Vision] Initializing YOLO-World (Zero-Shot Open Vocabulary)...")
                self.model = YOLOWorld("yolov8s-worldv2.pt")
                self.model.set_classes(["person", "helmet", "hardhat", "safety vest", "reflective vest", "goggles", "glasses", "gloves"])
                self.is_yolo_world = True
                print("[EdgeGuard Vision] YOLO-World active with PPE classes.")
            except Exception as e:
                print(f"[EdgeGuard Vision] YOLO-World load skipped ({e}). Operating in synthetic mode.")

    def process_frame(self, frame: np.ndarray, is_static: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Perform YOLO + ByteTrack inference on input BGR frame. Use is_static=True for independent images."""
        person_tracks: List[Dict[str, Any]] = []
        ppe_detections: List[Dict[str, Any]] = []

        if self.model is None:
            return person_tracks, ppe_detections

        try:
            if is_static:
                results = self.model(frame, verbose=False, conf=0.15)
            else:
                results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False, conf=0.15)
                
            if results and len(results) > 0:
                res = results[0]
                boxes = res.boxes
                if boxes is not None:
                    for box in boxes:
                        cls_id = int(box.cls[0].item()) if box.cls is not None else 0
                        cls_name = self.model.names.get(cls_id, "person") if hasattr(self.model, "names") else "person"
                        coords = box.xyxy[0].cpu().numpy().tolist()
                        conf = float(box.conf[0].item()) if box.conf is not None else 0.8
                        track_id = int(box.id[0].item()) if (box.id is not None and len(box.id) > 0) else None

                        if "person" in cls_name.lower() or cls_id == 0:
                            # Generate a temp ID for static images where tracking might fail
                            assigned_id = track_id if track_id is not None else (len(person_tracks) + 9901)
                            person_tracks.append({"track_id": assigned_id, "bbox": coords, "confidence": conf})
                        else:
                            ppe_detections.append({"class_name": cls_name.lower(), "bbox": coords, "confidence": conf})
        except Exception as e:
            print(f"[EdgeGuard Inference Error] {e}")

        return person_tracks, ppe_detections
