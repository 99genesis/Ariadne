"""Standard event topic definitions and payload schemas for Ariadne Event Bus.

All inter-module communication must use these strictly typed events
to maintain loose coupling and fault isolation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AriadneEvent(BaseModel):
    """Base event model from which all system events must inherit."""

    event_id: str = Field(..., description="Unique event topic identifier e.g. ariadne.events.TargetCreated")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_plugin: str = Field(default="core", description="ID of the module or plugin publishing this event")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data dictionary")


class TargetCreatedEvent(AriadneEvent):
    """Fired when a new target or vault is created."""

    event_id: str = Field(default="ariadne.events.TargetCreated")
    target_id: str = Field(...)
    target_type: str = Field(...)
    vault_name: str = Field(...)


class UsernameFoundEvent(AriadneEvent):
    """Fired when a username enum engine discovers a valid profile."""

    event_id: str = Field(default="ariadne.events.UsernameFound")
    target_id: str = Field(...)
    platform: str = Field(...)
    username: str = Field(...)
    profile_url: str = Field(...)
    avatar_url: Optional[str] = None
    confidence: float = Field(default=1.0)


class ImageGeoResolvedEvent(AriadneEvent):
    """Fired when Vision AI resolves multi-tier geolocation predictions."""

    event_id: str = Field(default="ariadne.events.ImageGeoResolved")
    target_id: str = Field(...)
    image_path: str = Field(...)
    district_guess: str = Field(default="Unknown")
    city_guess: str = Field(...)
    region_guess: str = Field(...)
    country_guess: str = Field(...)
    confidence: float = Field(default=0.8)
    provider_used: str = Field(...)


class LeakDiscoveredEvent(AriadneEvent):
    """Fired when data breach or password reset leak is confirmed."""

    event_id: str = Field(default="ariadne.events.LeakDiscovered")
    target_id: str = Field(...)
    email_or_phone: str = Field(...)
    breach_name: str = Field(...)
    confidence: float = Field(default=0.99)


class NoteCreatedEvent(AriadneEvent):
    """Fired when the Markdown layer creates or updates a note file."""

    event_id: str = Field(default="ariadne.events.NoteCreated")
    note_id: str = Field(...)
    target_id: str = Field(...)
    relative_path: str = Field(...)
    vault_name: str = Field(...)
