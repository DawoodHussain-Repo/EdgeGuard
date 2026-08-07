from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ROIPoint(BaseModel):
    """Normalized or absolute (x, y) coordinates of an ROI polygon vertex."""
    x: float = Field(..., description="X coordinate (0.0 to 1.0 or pixel x)")
    y: float = Field(..., description="Y coordinate (0.0 to 1.0 or pixel y)")


class ROIConfig(BaseModel):
    """Configuration for spatial Region of Interest (Restricted Safety Zone)."""
    enabled: bool = Field(default=True, description="Whether spatial ROI checking is enabled")
    label: str = Field(default="Restricted Zone Alpha", description="Name of the restricted ROI zone")
    polygon: List[ROIPoint] = Field(
        default_factory=lambda: [
            ROIPoint(x=0.1, y=0.4),
            ROIPoint(x=0.5, y=0.4),
            ROIPoint(x=0.5, y=0.95),
            ROIPoint(x=0.1, y=0.95)
        ],
        description="Polygon vertices defining restricted area"
    )


class Violation(BaseModel):
    """Detailed metadata for a flagged PPE or safety zone violation."""
    track_id: int = Field(..., description="Unique ByteTrack worker tracking ID")
    missing_gear: List[str] = Field(default_factory=list, description="List of missing required gear: ['helmet', 'vest']")
    in_restricted_zone: bool = Field(default=False, description="Whether worker is inside a restricted hazard zone")
    person_bbox: List[float] = Field(..., description="[x1, y1, x2, y2] bounding box coordinates")
    severity: str = Field(default="HIGH", description="Violation severity level: 'CRITICAL', 'HIGH', 'MEDIUM'")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class WorkerStatus(BaseModel):
    """Compliance state for an individual tracked worker."""
    track_id: int = Field(..., description="ByteTrack ID")
    bbox: List[float] = Field(..., description="[x1, y1, x2, y2] bounding box")
    has_helmet: bool = Field(default=False)
    has_vest: bool = Field(default=False)
    is_compliant: bool = Field(default=False)
    in_restricted_zone: bool = Field(default=False)


class TelemetryResponse(BaseModel):
    """Live telemetry payload returned by /api/v1/telemetry."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    active_workers: int = Field(..., description="Total active workers currently tracked")
    compliant_workers: int = Field(..., description="Workers wearing all required PPE")
    non_compliant_workers: int = Field(..., description="Workers missing one or more required PPE items")
    restricted_zone_violations: int = Field(default=0, description="Workers inside danger zone")
    violations: List[Violation] = Field(default_factory=list, description="List of current active worker violations")
    fps: float = Field(..., description="Current vision pipeline frames per second")
    latency_ms: float = Field(default=12.5, description="End-to-end frame processing latency in milliseconds")


class StreamStatus(BaseModel):
    """Status report for the active video stream."""
    stream_active: bool = True
    source: str = "Synthetic Test Generator / RTSP Feed"
    fps: float = 30.0
    frame_width: int = 1280
    frame_height: int = 720
    active_workers: int = 0
    total_violations: int = 0
