"""GraphVersioningEngine computing snapshots, SHA-256 structural hashes, and delta diffs."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from ariadne.graph.models import EntityEdge, EntityNode, GraphSnapshot


class GraphVersioningEngine:
    """Manages immutable snapshot generation, structural hashing, and version comparison deltas."""

    @staticmethod
    def compute_snapshot_hash(nodes: List[EntityNode], edges: List[EntityEdge]) -> str:
        """Compute SHA-256 hash representing the graph topology and canonical node attributes."""
        nodes_sorted = sorted([n.canonical_id for n in nodes])
        edges_sorted = sorted([f"{e.source_id}->{e.target_id}:{round(e.weight, 2)}" for e in edges])
        raw = f"nodes:{nodes_sorted}|edges:{edges_sorted}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def create_snapshot(
        cls,
        target_id: str,
        version: int,
        nodes: List[EntityNode],
        edges: List[EntityEdge],
    ) -> GraphSnapshot:
        """Create a validated GraphSnapshot with structural hash."""
        shash = cls.compute_snapshot_hash(nodes, edges)
        return GraphSnapshot(
            snapshot_id=f"snapshot:{target_id}:v{version}",
            target_id=target_id,
            version=version,
            timestamp=datetime.now(timezone.utc),
            nodes=nodes,
            edges=edges,
            hash_summary=shash,
        )

    @classmethod
    def diff_snapshots(cls, v1: GraphSnapshot, v2: GraphSnapshot) -> Dict[str, Any]:
        """Compute delta difference between two snapshots (added/removed nodes and edge weight shifts)."""
        nodes_v1 = {n.canonical_id: n for n in v1.nodes}
        nodes_v2 = {n.canonical_id: n for n in v2.nodes}

        added_nodes = [n for cid, n in nodes_v2.items() if cid not in nodes_v1]
        removed_nodes = [n for cid, n in nodes_v1.items() if cid not in nodes_v2]

        edges_v1 = {e.edge_id: e for e in v1.edges}
        edges_v2 = {e.edge_id: e for e in v2.edges}

        weight_changes = []
        for eid, e2 in edges_v2.items():
            if eid in edges_v1:
                e1 = edges_v1[eid]
                if abs(e2.weight - e1.weight) > 0.01:
                    weight_changes.append({"edge_id": eid, "old_weight": e1.weight, "new_weight": e2.weight})

        return {
            "target_id": v1.target_id,
            "v1_version": v1.version,
            "v2_version": v2.version,
            "added_nodes_count": len(added_nodes),
            "removed_nodes_count": len(removed_nodes),
            "added_nodes": [n.canonical_id for n in added_nodes],
            "removed_nodes": [n.canonical_id for n in removed_nodes],
            "weight_changes": weight_changes,
        }
