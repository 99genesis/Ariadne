"""GraphRepository for storing and querying versioned graph snapshots across targets."""

from typing import Any, Dict, List, Optional
from ariadne.graph.models import GraphSnapshot
from ariadne.graph.versioning import GraphVersioningEngine


class GraphRepository:
    """In-memory and persistence-ready repository for target graph snapshots and history."""

    def __init__(self) -> None:
        # Map target_id -> list of GraphSnapshot ordered by version ascending
        self._snapshots: Dict[str, List[GraphSnapshot]] = {}

    def store_snapshot(self, snapshot: GraphSnapshot) -> GraphSnapshot:
        """Store a new snapshot version for the target."""
        target_id = snapshot.target_id
        history = self._snapshots.setdefault(target_id, [])
        history.append(snapshot)
        history.sort(key=lambda s: s.version)
        return snapshot

    def get_latest_snapshot(self, target_id: str) -> Optional[GraphSnapshot]:
        """Retrieve the latest graph snapshot version for a target."""
        history = self._snapshots.get(target_id, [])
        return history[-1] if history else None

    def get_snapshot_history(self, target_id: str) -> List[GraphSnapshot]:
        """Retrieve full version snapshot history for a target."""
        return self._snapshots.get(target_id, [])

    def get_delta(self, target_id: str, v1_num: int, v2_num: int) -> Optional[Dict[str, Any]]:
        """Compute delta difference between two historical version numbers."""
        history = {s.version: s for s in self._snapshots.get(target_id, [])}
        if v1_num not in history or v2_num not in history:
            return None
        return GraphVersioningEngine.diff_snapshots(history[v1_num], history[v2_num])
