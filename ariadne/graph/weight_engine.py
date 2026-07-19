"""GraphWeightEngine computing dynamic edge weights from frequency, priority, and verification."""

from ariadne.graph.models import EntityEdge


class GraphWeightEngine:
    """Computes dynamic relationship confidence weights between graph nodes."""

    @classmethod
    def compute_edge_weight(
        cls,
        evidence_count: int,
        base_confidence: float = 0.5,
        is_verified: bool = False,
        relation_type: str = "associated_with",
    ) -> float:
        """Compute edge weight taking into account observation frequency and verification status."""
        weight = base_confidence

        # Frequency boost
        if evidence_count >= 5:
            weight += 0.25
        elif evidence_count >= 3:
            weight += 0.15
        elif evidence_count >= 2:
            weight += 0.10

        # Relation type boosts
        if relation_type in ("alias_of", "same_as"):
            weight += 0.15
        elif relation_type in ("bio_link", "owns"):
            weight += 0.10

        if is_verified:
            weight = max(weight, 0.85)

        return round(min(1.0, max(0.0, weight)), 4)
