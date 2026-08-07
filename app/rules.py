import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from app.schemas import Violation, WorkerStatus, ROIConfig, ROIPoint


def point_in_polygon(px: float, py: float, polygon: List[Tuple[float, float]]) -> bool:
    """
    Ray-casting algorithm to determine if a point (px, py) lies inside a 2D polygon.
    polygon is a list of (x, y) coordinate pairs.
    """
    num_pts = len(polygon)
    if num_pts < 3:
        return False

    inside = False
    p1x, p1y = polygon[0]
    for i in range(num_pts + 1):
        p2x, p2y = polygon[i % num_pts]
        if py > min(p1y, p2y):
            if py <= max(p1y, p2y):
                if px <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or px <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def box_containment_ratio(inner_box: List[float], outer_box: List[float]) -> float:
    """
    Calculate what fraction of inner_box area lies inside outer_box.
    Boxes formatted as [x1, y1, x2, y2].
    """
    ix1, iy1, ix2, iy2 = inner_box
    ox1, oy1, ox2, oy2 = outer_box

    # Intersection coordinates
    inter_x1 = max(ix1, ox1)
    inter_y1 = max(iy1, oy1)
    inter_x2 = min(ix2, ox2)
    inter_y2 = min(iy2, oy2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    inner_area = (ix2 - ix1) * (iy2 - iy1)
    if inner_area <= 0:
        return 0.0

    return inter_area / inner_area


class PPEComplianceEngine:
    """
    Spatial safety compliance engine matching ByteTrack worker tracks with PPE detections
    and dynamic spatial hazard ROIs.
    """

    def __init__(self, roi_config: Optional[ROIConfig] = None):
        self.roi_config = roi_config or ROIConfig()

    def update_roi(self, new_config: ROIConfig):
        """Update active ROI configuration dynamically."""
        self.roi_config = new_config

    def evaluate_frame(
        self,
        person_tracks: List[Dict[str, Any]],
        ppe_detections: List[Dict[str, Any]],
        frame_width: int = 1280,
        frame_height: int = 720
    ) -> Tuple[List[WorkerStatus], List[Violation], Dict[str, Any]]:
        """
        Evaluate frame detections:
        - person_tracks: [{"track_id": 1, "bbox": [x1, y1, x2, y2], "confidence": 0.85}, ...]
        - ppe_detections: [{"class_name": "helmet", "bbox": [x1, y1, x2, y2], "confidence": 0.90}, ...]
        """
        worker_statuses: List[WorkerStatus] = []
        active_violations: List[Violation] = []

        # Convert ROI points to pixel coordinates
        roi_polygon_pixels: List[Tuple[float, float]] = []
        if self.roi_config.enabled and self.roi_config.polygon:
            for pt in self.roi_config.polygon:
                # Handle both normalized (0..1) and absolute pixel coords
                px = pt.x * frame_width if pt.x <= 1.0 else pt.x
                py = pt.y * frame_height if pt.y <= 1.0 else pt.y
                roi_polygon_pixels.append((px, py))

        # Classify PPE items
        helmets = [d for d in ppe_detections if d.get("class_name") in ["helmet", "head_gear", "hard_hat"]]
        vests = [d for d in ppe_detections if d.get("class_name") in ["vest", "safety_vest", "high_vis"]]

        # Explicit negative detections if model supports no-helmet/no-vest classes
        no_helmets = [d for d in ppe_detections if d.get("class_name") in ["no_helmet", "no_hat"]]
        no_vests = [d for d in ppe_detections if d.get("class_name") in ["no_vest"]]

        for person in person_tracks:
            track_id = int(person["track_id"])
            p_bbox = person["bbox"]  # [x1, y1, x2, y2]
            px1, py1, px2, py2 = p_bbox

            person_height = max(1.0, py2 - py1)
            # Head ROI (top 35% of person box)
            head_box = [px1, py1, px2, py1 + 0.35 * person_height]
            # Torso ROI (middle 60% of person box)
            torso_box = [px1, py1 + 0.20 * person_height, px2, py2 - 0.10 * person_height]

            # 1. Helmet match test
            has_helmet = False
            for h in helmets:
                ratio = box_containment_ratio(h["bbox"], head_box)
                if ratio > 0.3 or box_containment_ratio(h["bbox"], p_bbox) > 0.4:
                    has_helmet = True
                    break

            # 2. Vest match test
            has_vest = False
            for v in vests:
                ratio = box_containment_ratio(v["bbox"], torso_box)
                if ratio > 0.3 or box_containment_ratio(v["bbox"], p_bbox) > 0.4:
                    has_vest = True
                    break

            # Check explicit missing gear flags if present
            for nh in no_helmets:
                if box_containment_ratio(nh["bbox"], head_box) > 0.3:
                    has_helmet = False

            for nv in no_vests:
                if box_containment_ratio(nv["bbox"], torso_box) > 0.3:
                    has_vest = False

            # 3. Restricted zone check (person foot center point)
            foot_center_x = (px1 + px2) / 2.0
            foot_center_y = py2
            in_restricted_zone = False
            if roi_polygon_pixels:
                in_restricted_zone = point_in_polygon(foot_center_x, foot_center_y, roi_polygon_pixels)

            # Determine missing gear
            missing_gear = []
            if not has_helmet:
                missing_gear.append("helmet")
            if not has_vest:
                missing_gear.append("vest")

            is_compliant = (len(missing_gear) == 0) and not in_restricted_zone

            status = WorkerStatus(
                track_id=track_id,
                bbox=[round(c, 2) for c in p_bbox],
                has_helmet=has_helmet,
                has_vest=has_vest,
                is_compliant=is_compliant,
                in_restricted_zone=in_restricted_zone
            )
            worker_statuses.append(status)

            # If violation detected, record it
            if missing_gear or in_restricted_zone:
                severity = "CRITICAL" if (in_restricted_zone and missing_gear) else ("HIGH" if len(missing_gear) > 1 else "MEDIUM")
                violation = Violation(
                    track_id=track_id,
                    missing_gear=missing_gear,
                    in_restricted_zone=in_restricted_zone,
                    person_bbox=[round(c, 2) for c in p_bbox],
                    severity=severity
                )
                active_violations.append(violation)

        total_workers = len(worker_statuses)
        compliant_count = sum(1 for w in worker_statuses if w.is_compliant)
        non_compliant_count = total_workers - compliant_count
        zone_violations_count = sum(1 for w in worker_statuses if w.in_restricted_zone)

        summary = {
            "active_workers": total_workers,
            "compliant_workers": compliant_count,
            "non_compliant_workers": non_compliant_count,
            "restricted_zone_violations": zone_violations_count,
        }

        return worker_statuses, active_violations, summary
