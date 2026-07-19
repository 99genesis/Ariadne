"""Pydantic domain models for Multi-Target Workspace configuration and directory paths.

Enforces strict schema validation for each target's config.json and directory mapping.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TargetWorkspaceConfig(BaseModel):
    """Configuration and metadata persisted in <Target_Root>/config.json."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    target_name: str = Field(..., description="Unique target identifier (folder name)")
    target_type: str = Field(default="username", description="Type of target e.g. username, person, domain")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 last update timestamp",
    )
    description: str = Field(default="", description="Optional description of the target")
    aliases: List[str] = Field(default_factory=list, description="Known aliases/usernames for this target")
    last_scan: Optional[str] = Field(default=None, description="ISO-8601 timestamp of last scan")
    favorite: bool = Field(default=False, description="Whether this target is marked as favorite")
    tags: List[str] = Field(default_factory=list, description="Categorical tags for this target")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom extensible metadata")


class TargetWorkspacePaths(BaseModel):
    """Absolute directory and file paths scoped to a specific target workspace."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    target_name: str
    target_root: Path
    vault_dir: Path
    db_path: Path
    cache_dir: Path
    reports_dir: Path
    attachments_dir: Path
    entities_dir: Path
    relations_dir: Path
    timeline_dir: Path
    history_dir: Path
    config_file: Path
