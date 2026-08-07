import cv2
import time
import math
import numpy as np
import threading
from typing import Generator, Optional, Dict, Any, List, Tuple
from datetime import datetime

from app.schemas import TelemetryResponse, Violation, WorkerStatus, ROIConfig, ROIPoint
from app.rules import PPEComplianceEngine, point_in_polygon

# Try importing ultralytics YOLO if available
try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


class VisionPipeline:
    """
    Real-time vision processing pipeline combining YOLOv8/YOLOv11 detection,
    ByteTrack multi-object tracking, spatial ROI safety enforcement, and low-latency frame streaming.
    Includes high-performance synthetic demonstration mode for immediate out-of-the-box operation.
    """

    def __init__(
        self,
        model_path: Optional[str] = "weights/ppe_yolov8n.pt",
        video_source: Optional[str] = None,
        frame_width: int = 1280,
        frame_height: int = 720,
        fps_target: int = 30
    ):
        self.model_path = model_path
        self.video_source = video_source
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps_target = fps_target

        self.rules_engine = PPEComplianceEngine()
        self.lock = threading.Lock()
        self.is_running = False

        # Latest processed frame (encoded JPEG bytes)
        self._latest_jpeg: Optional[bytes] = None
        self._latest_telemetry: Optional[TelemetryResponse] = None

        # Metrics
        self.fps = 30.0
        self.start_time = time.time()
        self.frame_count = 0
        self.last_frame_time = time.time()

        # Initialize Model if available
        self.model = None
        if ULTRALYTICS_AVAILABLE and model_path:
            try:
                self.model = YOLO(model_path)
                print(f"[EdgeGuard Vision] Successfully loaded YOLO model from {model_path}")
            except Exception as e:
                print(f"[EdgeGuard Vision] Custom model load skipped ({e}). Operating in adaptive pipeline mode.")

        # Synthetic worker states for high-framerate demo stream
        self._demo_workers = [
            {"id": 1, "x": 180, "y": 280, "vx": 1.2, "vy": 0.8, "has_helmet": True, "has_vest": True},
            {"id": 2, "x": 580, "y": 420, "vx": -1.5, "vy": 0.6, "has_helmet": False, "has_vest": True},
            {"id": 3, "x": 320, "y": 500, "vx": 0.9, "vy": -1.1, "has_helmet": True, "has_vest": False},
            {"id": 4, "x": 750, "y": 320, "vx": -0.8, "vy": -0.7, "has_helmet": True, "has_vest": True},
            {"id": 5, "x": 220, "y": 380, "vx": 1.4, "vy": -0.5, "has_helmet": False, "has_vest": False},
        ]

    def start(self):
        """Start background vision processing thread."""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.thread.start()
            print("[EdgeGuard Vision] Pipeline loop started successfully.")

    def stop(self):
        """Stop background vision processing thread."""
        self.is_running = False

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Return latest JPEG bytes thread-safely."""
        with self.lock:
            return self._latest_jpeg

    def get_latest_telemetry(self) -> TelemetryResponse:
        """Return latest telemetry snapshot thread-safely."""
        with self.lock:
            if self._latest_telemetry:
                return self._latest_telemetry
            return TelemetryResponse(
                active_workers=0,
                compliant_workers=0,
                non_compliant_workers=0,
                restricted_zone_violations=0,
                violations=[],
                fps=self.fps,
                latency_ms=10.0
            )

    def update_roi(self, new_config: ROIConfig):
        """Update ROI rules engine configuration."""
        with self.lock:
            self.rules_engine.update_roi(new_config)

    def get_roi_config(self) -> ROIConfig:
        """Get current ROI configuration."""
        with self.lock:
            return self.rules_engine.roi_config

    def _processing_loop(self):
        """Background execution loop acquiring frames and performing computer vision analysis."""
        cap = None
        if self.video_source is not None and str(self.video_source) != "":
            try:
                source_input = int(self.video_source) if str(self.video_source).isdigit() else self.video_source
                cap = cv2.VideoCapture(source_input)
                if not cap.isOpened():
                    print(f"[EdgeGuard Vision] Could not open video source {self.video_source}. Falling back to Synthetic Demo Feed.")
                    cap = None
            except Exception as ex:
                print(f"[EdgeGuard Vision] Video capture error ({ex}). Falling back to Synthetic Demo Feed.")
                cap = None

        while self.is_running:
            loop_start = time.time()

            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video
                    ret, frame = cap.read()

                if ret and frame is not None:
                    frame = cv2.resize(frame, (self.frame_width, self.frame_height))
                    processed_frame, telemetry = self._process_real_frame(frame)
                else:
                    processed_frame, telemetry = self._generate_synthetic_frame()
            else:
                processed_frame, telemetry = self._generate_synthetic_frame()

            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', processed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            jpeg_bytes = buffer.tobytes()

            # Calculate FPS
            self.frame_count += 1
            now = time.time()
            elapsed = now - self.last_frame_time
            if elapsed >= 1.0:
                self.fps = round(self.frame_count / elapsed, 1)
                self.frame_count = 0
                self.last_frame_time = now

            telemetry.fps = self.fps
            telemetry.latency_ms = round((time.time() - loop_start) * 1000.0, 1)

            with self.lock:
                self._latest_jpeg = jpeg_bytes
                self._latest_telemetry = telemetry

            # Rate limit processing loop
            target_period = 1.0 / self.fps_target
            proc_time = time.time() - loop_start
            if proc_time < target_period:
                time.sleep(target_period - proc_time)

        if cap is not None:
            cap.release()

    def _process_real_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, TelemetryResponse]:
        """Perform YOLO + ByteTrack inference on actual OpenCV image frame."""
        person_tracks = []
        ppe_detections = []

        if self.model is not None:
            try:
                results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
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
                                if track_id is not None:
                                    person_tracks.append({
                                        "track_id": track_id,
                                        "bbox": coords,
                                        "confidence": conf
                                    })
                            else:
                                ppe_detections.append({
                                    "class_name": cls_name.lower(),
                                    "bbox": coords,
                                    "confidence": conf
                                })
            except Exception as e:
                print(f"[EdgeGuard Inference Error] {e}")

        worker_statuses, active_violations, summary = self.rules_engine.evaluate_frame(
            person_tracks, ppe_detections, self.frame_width, self.frame_height
        )

        annotated_frame = self._draw_annotations(frame, worker_statuses, active_violations)

        telemetry = TelemetryResponse(
            active_workers=summary["active_workers"],
            compliant_workers=summary["compliant_workers"],
            non_compliant_workers=summary["non_compliant_workers"],
            restricted_zone_violations=summary["restricted_zone_violations"],
            violations=active_violations,
            fps=self.fps,
            latency_ms=12.0
        )

        return annotated_frame, telemetry

    def _generate_synthetic_frame(self) -> Tuple[np.ndarray, TelemetryResponse]:
        """
        Generates a realistic high-resolution construction site monitoring frame
        with animated personnel, ByteTrack tracks, spatial compliance, and HUD elements.
        """
        # Create dark industrial background gradient canvas
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        frame[:, :] = (15, 20, 28)

        # Draw site grid & architectural structural lines
        for y in range(0, self.frame_height, 60):
            cv2.line(frame, (0, y), (self.frame_width, y), (25, 33, 44), 1)
        for x in range(0, self.frame_width, 80):
            cv2.line(frame, (x, 0), (x, self.frame_height), (25, 33, 44), 1)

        # Update synthetic worker positions
        person_tracks = []
        ppe_detections = []

        for w in self._demo_workers:
            # Move worker
            w["x"] += w["vx"]
            w["y"] += w["vy"]

            # Bounce off screen boundaries
            if w["x"] < 120 or w["x"] > self.frame_width - 200:
                w["vx"] *= -1.0
            if w["y"] < 200 or w["y"] > self.frame_height - 180:
                w["vy"] *= -1.0

            w_width, w_height = 90, 210
            x1, y1 = w["x"], w["y"]
            x2, y2 = x1 + w_width, y1 + w_height
            bbox = [x1, y1, x2, y2]

            person_tracks.append({
                "track_id": w["id"],
                "bbox": bbox,
                "confidence": 0.94
            })

            # Add synthetic helmet detection
            if w["has_helmet"]:
                ppe_detections.append({
                    "class_name": "helmet",
                    "bbox": [x1 + 10, y1 + 5, x2 - 10, y1 + 50],
                    "confidence": 0.92
                })

            # Add synthetic vest detection
            if w["has_vest"]:
                ppe_detections.append({
                    "class_name": "vest",
                    "bbox": [x1 + 5, y1 + 55, x2 - 5, y2 - 40],
                    "confidence": 0.89
                })

        worker_statuses, active_violations, summary = self.rules_engine.evaluate_frame(
            person_tracks, ppe_detections, self.frame_width, self.frame_height
        )

        annotated_frame = self._draw_annotations(frame, worker_statuses, active_violations)

        telemetry = TelemetryResponse(
            active_workers=summary["active_workers"],
            compliant_workers=summary["compliant_workers"],
            non_compliant_workers=summary["non_compliant_workers"],
            restricted_zone_violations=summary["restricted_zone_violations"],
            violations=active_violations,
            fps=self.fps,
            latency_ms=8.5
        )

        return annotated_frame, telemetry

    def _draw_annotations(
        self,
        frame: np.ndarray,
        worker_statuses: List[WorkerStatus],
        active_violations: List[Violation]
    ) -> np.ndarray:
        """Render ROI polygon, worker bounding boxes, status badges, and top HUD metrics."""
        overlay = frame.copy()

        # 1. Render Restricted Zone ROI Polygon
        roi_config = self.rules_engine.roi_config
        if roi_config.enabled and roi_config.polygon:
            pts = []
            for pt in roi_config.polygon:
                px = int(pt.x * self.frame_width if pt.x <= 1.0 else pt.x)
                py = int(pt.y * self.frame_height if pt.y <= 1.0 else pt.y)
                pts.append([px, py])

            pts_np = np.array(pts, np.int32).reshape((-1, 1, 2))
            
            # Fill semi-transparent hazard zone
            cv2.fillPoly(overlay, [pts_np], (15, 25, 120))
            cv2.polylines(frame, [pts_np], isClosed=True, color=(30, 40, 230), thickness=2)
            cv2.polylines(overlay, [pts_np], isClosed=True, color=(30, 160, 255), thickness=3)

            # Zone label
            if len(pts) > 0:
                lx, ly = pts[0]
                cv2.rectangle(frame, (lx, ly - 30), (lx + 240, ly), (15, 25, 120), -1)
                cv2.putText(frame, f"DANGER ROI: {roi_config.label}", (lx + 8, ly - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)

        # Blend overlay for transparent ROI fill
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

        # 2. Render Worker Bounding Boxes & Badges
        for w in worker_statuses:
            x1, y1, x2, y2 = [int(c) for c in w.bbox]
            track_id = w.track_id

            # Color coding
            if w.is_compliant:
                box_color = (60, 180, 75)   # Emerald / Green
                label_bg = (30, 120, 50)
                status_text = "COMPLIANT"
            elif w.in_restricted_zone and not (w.has_helmet and w.has_vest):
                box_color = (40, 40, 235)   # Critical Crimson / Red
                label_bg = (20, 20, 180)
                status_text = "CRITICAL HAZARD"
            else:
                box_color = (30, 165, 245)  # Amber / Warning
                label_bg = (20, 100, 180)
                status_text = "PPE VIOLATION"

            # Draw worker bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

            # Header ID badge
            badge_text = f"ID #{track_id:02d} | {status_text}"
            (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - 26)), (x1 + tw + 14, y1), label_bg, -1)
            cv2.putText(frame, badge_text, (x1 + 7, max(12, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            # Gear Pills on bottom of bounding box
            helmet_str = "H: OK" if w.has_helmet else "H: MISSING"
            vest_str = "V: OK" if w.has_vest else "V: MISSING"
            gear_text = f"{helmet_str}  {vest_str}"

            gear_bg = (20, 25, 35)
            cv2.rectangle(frame, (x1, y2), (x1 + 140, y2 + 20), gear_bg, -1)
            h_color = (80, 220, 100) if w.has_helmet else (60, 60, 240)
            v_color = (80, 220, 100) if w.has_vest else (60, 60, 240)

            cv2.putText(frame, helmet_str, (x1 + 6, y2 + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, h_color, 1, cv2.LINE_AA)
            cv2.putText(frame, vest_str, (x1 + 75, y2 + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, v_color, 1, cv2.LINE_AA)

        # 3. Top HUD Banner
        hud_bg = frame[:48, :].copy()
        cv2.rectangle(frame, (0, 0), (self.frame_width, 48), (10, 14, 22), -1)

        # Branding
        cv2.putText(frame, "EDGEGUARD-AI", (16, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 255), 2, cv2.LINE_AA)

        # Telemetry Summary Text
        compliant_n = sum(1 for w in worker_statuses if w.is_compliant)
        violation_n = len(worker_statuses) - compliant_n
        stats_str = f"WORKERS: {len(worker_statuses)}  |  COMPLIANT: {compliant_n}  |  VIOLATIONS: {violation_n}  |  FPS: {self.fps:.1f}"

        cv2.putText(frame, stats_str, (210, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 225, 235), 1, cv2.LINE_AA)

        # Live Recording Indicator
        cv2.circle(frame, (self.frame_width - 120, 24), 6, (0, 0, 255), -1)
        cv2.putText(frame, "LIVE PIPELINE", (self.frame_width - 105, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

        return frame

    def generate_mjpeg_stream(self) -> Generator[bytes, None, None]:
        """
        FastAPI Stream Generator returning continuous multipart MJPEG frame chunks.
        """
        while True:
            jpeg_bytes = self.get_latest_jpeg()
            if jpeg_bytes is not None:
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n'
                )
            time.sleep(1.0 / self.fps_target)


# Global singleton instance
pipeline = VisionPipeline()
