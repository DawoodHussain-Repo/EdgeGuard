import math
from typing import List, Dict, Any, Tuple
from app.core.schemas import WorkerStatus, Violation, DetectedPPE, MissingPPE

def box_containment_ratio(small_box: List[float], large_box: List[float]) -> float:
    """Calculate ratio of small_box area that lies within large_box."""
    s_x1, s_y1, s_x2, s_y2 = small_box
    l_x1, l_y1, l_x2, l_y2 = large_box
    
    inter_x1 = max(s_x1, l_x1)
    inter_y1 = max(s_y1, l_y1)
    inter_x2 = min(s_x2, l_x2)
    inter_y2 = min(s_y2, l_y2)
    
    if inter_x1 < inter_x2 and inter_y1 < inter_y2:
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        small_area = max(1e-5, (s_x2 - s_x1) * (s_y2 - s_y1))
        return inter_area / small_area
    return 0.0

class PPEComplianceEngine:
    def __init__(self):
        pass

    def evaluate_frame(
        self,
        person_tracks: List[Dict[str, Any]],
        ppe_detections: List[Dict[str, Any]],
        frame_width: int = 1280,
        frame_height: int = 720
    ) -> Tuple[List[WorkerStatus], List[Violation], Dict[str, Any]]:
        """Evaluate frame worker tracks against PPE items."""
        worker_statuses: List[WorkerStatus] = []
        active_violations: List[Violation] = []

        # Classify PPE items
        helmets = [d for d in ppe_detections if d.get("class_name") in ["helmet", "head_gear", "hard_hat", "hardhat"]]
        vests = [d for d in ppe_detections if d.get("class_name") in ["vest", "safety_vest", "high_vis", "safety vest", "reflective vest"]]
        goggles = [d for d in ppe_detections if d.get("class_name") in ["goggles", "glasses"]]
        gloves = [d for d in ppe_detections if d.get("class_name") in ["gloves", "glove"]]

        for person in person_tracks:
            track_id = int(person["track_id"])
            p_bbox = person["bbox"]
            px1, py1, px2, py2 = p_bbox

            person_height = max(1.0, py2 - py1)
            head_box = [px1, py1, px2, py1 + 0.35 * person_height]
            torso_box = [px1, py1 + 0.20 * person_height, px2, py2 - 0.10 * person_height]
            face_box = [px1, py1 + 0.10 * person_height, px2, py1 + 0.40 * person_height]
            hands_box = [px1, py1 + 0.40 * person_height, px2, py2] # Lower half of body roughly for hands

            def find_matching_gear(gear_list, region_box, threshold1=0.3, threshold2=0.4):
                for g in gear_list:
                    if box_containment_ratio(g["bbox"], region_box) > threshold1 or box_containment_ratio(g["bbox"], p_bbox) > threshold2:
                        return g["bbox"]
                return None

            helmet_bbox = find_matching_gear(helmets, head_box)
            vest_bbox = find_matching_gear(vests, torso_box)
            goggles_bbox = find_matching_gear(goggles, face_box)
            gloves_bbox = find_matching_gear(gloves, hands_box)

            present_gear = []
            missing_gear_boxes = []
            missing_gear_names = []

            if helmet_bbox:
                present_gear.append(DetectedPPE(label="Helmet", bbox=helmet_bbox))
            else:
                missing_gear_names.append("helmet")
                missing_gear_boxes.append(MissingPPE(label="NO HELMET", bbox=head_box))

            if vest_bbox:
                present_gear.append(DetectedPPE(label="Vest", bbox=vest_bbox))
            else:
                missing_gear_names.append("vest")
                missing_gear_boxes.append(MissingPPE(label="NO VEST", bbox=torso_box))

            if goggles_bbox:
                present_gear.append(DetectedPPE(label="Goggles", bbox=goggles_bbox))
            else:
                missing_gear_names.append("goggles")
                missing_gear_boxes.append(MissingPPE(label="NO GOGGLES", bbox=face_box))

            if gloves_bbox:
                present_gear.append(DetectedPPE(label="Gloves", bbox=gloves_bbox))
            else:
                missing_gear_names.append("gloves")
                missing_gear_boxes.append(MissingPPE(label="NO GLOVES", bbox=hands_box))

            is_compliant = (len(missing_gear_names) == 0)

            status = WorkerStatus(
                track_id=track_id,
                bbox=[round(c, 2) for c in p_bbox],
                has_helmet=bool(helmet_bbox),
                has_vest=bool(vest_bbox),
                has_goggles=bool(goggles_bbox),
                has_gloves=bool(gloves_bbox),
                is_compliant=is_compliant,
                present_gear=present_gear,
                missing_gear=missing_gear_boxes
            )
            worker_statuses.append(status)

            if missing_gear_names:
                severity = "HIGH" if len(missing_gear_names) > 1 else "MEDIUM"
                violation = Violation(
                    track_id=track_id,
                    missing_gear=missing_gear_names,
                    person_bbox=[round(c, 2) for c in p_bbox],
                    severity=severity
                )
                active_violations.append(violation)

        total_workers = len(worker_statuses)
        compliant_count = sum(1 for w in worker_statuses if w.is_compliant)

        summary = {
            "active_workers": total_workers,
            "compliant_workers": compliant_count,
            "non_compliant_workers": total_workers - compliant_count
        }

        return worker_statuses, active_violations, summary
