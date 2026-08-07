import cv2
import time
import threading
from typing import Generator, Optional, Dict, Any, Tuple

from app.core.schemas import TelemetryResponse
from app.core.rules import PPEComplianceEngine
from app.vision.detector import VisionDetector
from app.vision.synthetic import SyntheticGenerator
from app.vision.annotator import VisionAnnotator


class VisionPipeline:
    """Real-time vision processing orchestrator combining detection, spatial rules, and frame encoding."""

    def __init__(
        self,
        model_path: Optional[str] = "weights/ppe_yolov8n.pt",
        video_source: Optional[str] = None,
        frame_width: int = 1280,
        frame_height: int = 720,
        fps_target: int = 30
    ):
        self.video_source = video_source
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps_target = fps_target

        self.rules_engine = PPEComplianceEngine()
        self.detector = VisionDetector(model_path)
        self.synthetic = SyntheticGenerator(frame_width, frame_height)
        self.annotator = VisionAnnotator(frame_width, frame_height)

        self.lock = threading.Lock()
        self.is_running = False

        self._latest_jpeg: Optional[bytes] = None
        self._latest_telemetry: Optional[TelemetryResponse] = None

        self.fps = 30.0
        self.start_time = time.time()
        self.frame_count = 0
        self.last_frame_time = time.time()

    def start(self):
        """Start background processing loop thread."""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.thread.start()
            print("[EdgeGuard Vision] Pipeline loop started.")

    def stop(self):
        """Stop background processing loop thread."""
        self.is_running = False

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self.lock:
            return self._latest_jpeg

    def get_latest_telemetry(self) -> TelemetryResponse:
        with self.lock:
            if self._latest_telemetry:
                return self._latest_telemetry
            return TelemetryResponse(
                active_workers=0, compliant_workers=0, non_compliant_workers=0,
                violations=[], fps=self.fps, latency_ms=10.0
            )



    def set_video_source(self, source: Optional[str]):
        with self.lock:
            self.video_source = source
            print(f"[EdgeGuard Vision] Switched video source to: {source}")

    def trigger_mock_violation(self) -> Dict[str, Any]:
        with self.lock:
            return self.synthetic.trigger_mock_violation()

    def _processing_loop(self):
        cap = None
        if self.video_source is not None and str(self.video_source) != "":
            try:
                source_input = int(self.video_source) if str(self.video_source).isdigit() else self.video_source
                cap = cv2.VideoCapture(source_input)
                if not cap.isOpened():
                    cap = None
            except Exception:
                cap = None

        while self.is_running:
            loop_start = time.time()

            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()

                if ret and frame is not None:
                    frame = cv2.resize(frame, (self.frame_width, self.frame_height))
                    person_tracks, ppe_detections = self.detector.process_frame(frame)
                else:
                    frame, person_tracks, ppe_detections = self.synthetic.step()
            else:
                frame, person_tracks, ppe_detections = self.synthetic.step()

            worker_statuses, active_violations, summary = self.rules_engine.evaluate_frame(
                person_tracks, ppe_detections, self.frame_width, self.frame_height
            )

            annotated = self.annotator.draw_annotations(frame, worker_statuses, self.fps)
            _, buffer = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

            self.frame_count += 1
            now = time.time()
            elapsed = now - self.last_frame_time
            if elapsed >= 1.0:
                self.fps = round(self.frame_count / elapsed, 1)
                self.frame_count = 0
                self.last_frame_time = now

            telemetry = TelemetryResponse(
                active_workers=summary["active_workers"],
                compliant_workers=summary["compliant_workers"],
                non_compliant_workers=summary["non_compliant_workers"],
                violations=active_violations,
                fps=self.fps,
                latency_ms=round((time.time() - loop_start) * 1000.0, 1)
            )

            with self.lock:
                self._latest_jpeg = buffer.tobytes()
                self._latest_telemetry = telemetry

            target_period = 1.0 / self.fps_target
            proc_time = time.time() - loop_start
            if proc_time < target_period:
                time.sleep(target_period - proc_time)

        if cap is not None:
            cap.release()

    def generate_mjpeg_stream(self) -> Generator[bytes, None, None]:
        while True:
            jpeg_bytes = self.get_latest_jpeg()
            if jpeg_bytes is not None:
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
            time.sleep(1.0 / self.fps_target)


pipeline = VisionPipeline()
