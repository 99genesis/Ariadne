"""Pydantic domain models for Timeline Generator (`ariadne/timeline/models.py`)."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    """Single chronological event in the life of a target entity."""

    event_id: str = Field(..., description="Unique event ID e.g. evt:twitter:created")
    timestamp: datetime = Field(..., description="Chronological timestamp of the event")
    event_type: str = Field(default="discovery", description="Type e.g. creation, discovery, modification, breach")
    title: str = Field(..., description="Event title")
    description: str = Field(default="", description="Detailed summary")
    source_id: str = Field(default="system", description="Plugin or URL source")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)


class TargetTimeline(BaseModel):
    """Chronological event history across all intelligence findings for a target."""

    target_id: str = Field(..., description="Target ID")
    events: List[TimelineEvent] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    earliest_timestamp: Optional[datetime] = Field(default=None)
    latest_timestamp: Optional[datetime] = Field(default=None)
