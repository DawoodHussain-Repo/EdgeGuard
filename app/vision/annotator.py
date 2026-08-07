import cv2
import numpy as np
from typing import List
from app.core.schemas import WorkerStatus


class VisionAnnotator:
    """Visual overlay renderer for responsive worker annotations."""

    def __init__(self, frame_width: int = 1280, frame_height: int = 720):
        self.frame_width = frame_width
        self.frame_height = frame_height

    def _draw_dashed_rect(self, img, pt1, pt2, color, thickness, dash_length=10):
        """Draw a dashed rectangle."""
        x1, y1 = pt1
        x2, y2 = pt2
        
        # Draw top and bottom
        for x in range(x1, x2, dash_length * 2):
            cv2.line(img, (x, y1), (min(x + dash_length, x2), y1), color, thickness)
            cv2.line(img, (x, y2), (min(x + dash_length, x2), y2), color, thickness)
            
        # Draw left and right
        for y in range(y1, y2, dash_length * 2):
            cv2.line(img, (x1, y), (x1, min(y + dash_length, y2)), color, thickness)
            cv2.line(img, (x2, y), (x2, min(y + dash_length, y2)), color, thickness)

    def draw_annotations(
        self,
        frame: np.ndarray,
        worker_statuses: List[WorkerStatus],
        fps: float
    ) -> np.ndarray:
        """Render responsive bounding boxes and PPE gear labels."""
        overlay = frame.copy()
        
        frame_h, frame_w = frame.shape[:2]
        base_scale = max(0.4, min(frame_w, frame_h) / 1500.0)
        
        # Dim background slightly for contrast
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

        non_compliant_workers = []

        # 1. Render Worker Bounding Boxes & Gear
        for w in worker_statuses:
            x1, y1, x2, y2 = [int(c) for c in w.bbox]
            track_id = w.track_id
            
            box_width = x2 - x1
            box_height = y2 - y1
            
            # Responsive font scale for this specific worker
            worker_scale = max(0.3, min(1.0, box_width / 300.0))
            thickness = max(1, int(worker_scale * 3))

            if w.is_compliant:
                box_color = (60, 180, 75)
                label_bg = (30, 120, 50)
                status_text = "COMPLIANT"
            else:
                box_color = (30, 165, 245)
                label_bg = (20, 100, 180)
                status_text = "PPE VIOLATION"
                missing_str = ", ".join([mg.label.replace("NO ", "") for mg in w.missing_gear])
                non_compliant_workers.append(f"ID #{track_id:02d}: Missing {missing_str}")

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, max(1, thickness))

            # Main Badge
            badge_text = f"ID #{track_id:02d} | {status_text}"
            (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, worker_scale, thickness)
            cv2.rectangle(frame, (x1, max(0, y1 - th - 10)), (x1 + tw + 10, y1), label_bg, -1)
            cv2.putText(frame, badge_text, (x1 + 5, max(12, y1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, worker_scale, (255, 255, 255), thickness, cv2.LINE_AA)

            # Draw Present Gear
            for gear in w.present_gear:
                gx1, gy1, gx2, gy2 = [int(c) for c in gear.bbox]
                # Ensure within frame bounds
                gx1, gy1 = max(0, gx1), max(0, gy1)
                gx2, gy2 = min(frame_w, gx2), min(frame_h, gy2)
                
                cv2.rectangle(frame, (gx1, gy1), (gx2, gy2), (80, 220, 100), max(1, thickness))
                (gtw, gth), _ = cv2.getTextSize(gear.label, cv2.FONT_HERSHEY_SIMPLEX, worker_scale * 0.8, thickness)
                cv2.rectangle(frame, (gx1, max(0, gy1 - gth - 6)), (gx1 + gtw + 6, gy1), (30, 120, 50), -1)
                cv2.putText(frame, gear.label, (gx1 + 3, max(8, gy1 - 3)),
                            cv2.FONT_HERSHEY_SIMPLEX, worker_scale * 0.8, (255, 255, 255), thickness, cv2.LINE_AA)

            # Draw Missing Gear Regions
            for gear in w.missing_gear:
                mx1, my1, mx2, my2 = [int(c) for c in gear.bbox]
                mx1, my1 = max(0, mx1), max(0, my1)
                mx2, my2 = min(frame_w, mx2), min(frame_h, my2)
                
                # Draw dashed red rect
                self._draw_dashed_rect(frame, (mx1, my1), (mx2, my2), (40, 40, 235), max(1, thickness), dash_length=8)
                (mtw, mth), _ = cv2.getTextSize(gear.label, cv2.FONT_HERSHEY_SIMPLEX, worker_scale * 0.9, thickness)
                cv2.rectangle(frame, (mx1, max(0, my1 - mth - 6)), (mx1 + mtw + 6, my1), (20, 20, 180), -1)
                cv2.putText(frame, gear.label, (mx1 + 3, max(8, my1 - 3)),
                            cv2.FONT_HERSHEY_SIMPLEX, worker_scale * 0.9, (255, 255, 255), thickness, cv2.LINE_AA)

        # 2. Bottom Summary Banner (Only if there are violations)
        if non_compliant_workers:
            summary_h = 20 + len(non_compliant_workers) * 25
            cv2.rectangle(frame, (0, frame_h - summary_h), (frame_w, frame_h), (15, 20, 30), -1)
            
            cv2.putText(frame, "VIOLATION SUMMARY", (10, frame_h - summary_h + 18), 
                        cv2.FONT_HERSHEY_SIMPLEX, base_scale * 1.2, (40, 40, 235), max(1, int(base_scale * 3)), cv2.LINE_AA)
            
            y_offset = frame_h - summary_h + 40
            for text in non_compliant_workers:
                cv2.putText(frame, text, (10, y_offset), 
                            cv2.FONT_HERSHEY_SIMPLEX, base_scale, (200, 200, 200), max(1, int(base_scale * 2)), cv2.LINE_AA)
                y_offset += 25

        return frame
