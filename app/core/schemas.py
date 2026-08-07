from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DetectedPPE(BaseModel):
    label: str
    bbox: List[float]

class MissingPPE(BaseModel):
    label: str
    bbox: List[float]

class Violation(BaseModel):
    """Detailed metadata for a flagged PPE or safety zone violation."""
    track_id: int = Field(..., description="Unique ByteTrack worker tracking ID")
    missing_gear: List[str] = Field(default_factory=list, description="List of missing required gear: ['helmet', 'vest', 'goggles', 'gloves']")
    person_bbox: List[float] = Field(..., description="[x1, y1, x2, y2] bounding box coordinates")
    severity: str = Field(default="HIGH", description="Violation severity level: 'CRITICAL', 'HIGH', 'MEDIUM'")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

class WorkerStatus(BaseModel):
    """Compliance state for an individual tracked worker."""
    track_id: int = Field(..., description="ByteTrack ID")
    bbox: List[float] = Field(..., description="[x1, y1, x2, y2] bounding box")
    has_helmet: bool = Field(default=False)
    has_vest: bool = Field(default=False)
    has_goggles: bool = Field(default=False)
    has_gloves: bool = Field(default=False)
    is_compliant: bool = Field(default=False)
    present_gear: List[DetectedPPE] = Field(default_factory=list)
    missing_gear: List[MissingPPE] = Field(default_factory=list)

class TelemetryResponse(BaseModel):
    """Live telemetry payload returned by /api/v1/telemetry."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    active_workers: int = Field(..., description="Total active workers currently tracked")
    compliant_workers: int = Field(..., description="Workers wearing all required PPE")
    non_compliant_workers: int = Field(..., description="Workers missing one or more required PPE items")
    violations: List[Violation] = Field(default_factory=list, description="List of current active worker violations")
    fps: float = Field(..., description="Current vision pipeline frames per second")
    latency_ms: float = Field(default=12.5, description="End-to-end frame processing latency in milliseconds")

class StreamStatus(BaseModel):
    """Status report for active video stream."""
    stream_active: bool = Field(...)
    source: str = Field(...)
    fps: float = Field(...)
    frame_width: int = Field(...)
    frame_height: int = Field(...)
    active_workers: int = Field(...)
    total_violations: int = Field(...)
