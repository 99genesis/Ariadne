"""Pydantic domain models representing nodes, weighted edges, and versioned snapshots in the intelligence graph."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EntityNode(BaseModel):
    """Represents a resolved, canonical entity node within the intelligence graph."""

    node_id: str = Field(..., description="Unique canonical ID (e.g. username:twitter:scarface)")
    canonical_id: str = Field(..., description="Canonical ID used across deduplication")
    entity_type: str = Field(default="unknown", description="Category e.g. username, email, phone, domain")
    label: str = Field(..., description="Human-readable label for display")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Merged properties")
    aliases: List[str] = Field(default_factory=list, description="Known variations or aliases")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provenance_ids: List[str] = Field(default_factory=list, description="Cryptographic provenance hashes")


class EntityEdge(BaseModel):
    """Represents a directed or undirected weighted relationship between two nodes."""

    edge_id: str = Field(..., description="Unique edge identifier e.g. src->dst:relation")
    source_id: str = Field(..., description="Source node_id")
    target_id: str = Field(..., description="Target node_id")
    relation_type: str = Field(default="associated_with", description="Relationship type e.g. alias_of, owns, bio_link")
    weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Dynamic confidence weight")
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_count: int = Field(default=1, description="Number of times this relation was observed")


class GraphSnapshot(BaseModel):
    """Immutable version snapshot of an intelligence graph for historical tracking and rollback."""

    snapshot_id: str = Field(..., description="Snapshot identifier e.g. snapshot:target:v1")
    target_id: str = Field(..., description="Target entity ID associated with this graph")
    version: int = Field(default=1, description="Incremental version number")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    nodes: List[EntityNode] = Field(default_factory=list)
    edges: List[EntityEdge] = Field(default_factory=list)
    hash_summary: str = Field(default="", description="Cryptographic SHA-256 hash of the graph structure")
