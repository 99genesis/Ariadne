"""EntityResolver merging duplicate node findings and constructing canonical graph nodes and edges."""

from datetime import datetime, timezone
from typing import Dict, List, Tuple
from ariadne.core.models import IntelligenceResult
from ariadne.graph.canonicalizer import EntityCanonicalizer
from ariadne.graph.models import EntityEdge, EntityNode
from ariadne.graph.weight_engine import GraphWeightEngine


class EntityResolver:
    """Resolves raw intelligence results into canonical graph nodes and weighted edges."""

    @classmethod
    def resolve_from_results(
        cls,
        root_target_id: str,
        root_display_name: str,
        results: List[IntelligenceResult],
    ) -> Tuple[List[EntityNode], List[EntityEdge]]:
        """Process intelligence results and build unique canonical nodes with weighted edges to the root target."""
        now = datetime.now(timezone.utc)
        root_canon = EntityCanonicalizer.canonicalize("target", root_target_id)
        root_node = EntityNode(
            node_id=root_canon,
            canonical_id=root_canon,
            entity_type="target",
            label=root_display_name,
            attributes={"target_id": root_target_id},
        )

        nodes_map: Dict[str, EntityNode] = {root_canon: root_node}
        edges_map: Dict[str, EntityEdge] = {}

        for r in results:
            meta = r.metadata or {}
            plat = meta.get("platform", r.source_plugin or "")
            label_val = getattr(r, "url", None) or meta.get("url") or meta.get("profile_url") or r.title or "finding"
            canon_id = EntityCanonicalizer.canonicalize(r.entity_type, label_val, platform=plat)

            # Check if node exists to merge/update
            if canon_id not in nodes_map:
                nodes_map[canon_id] = EntityNode(
                    node_id=canon_id,
                    canonical_id=canon_id,
                    entity_type=r.entity_type,
                    label=r.title or label_val,
                    attributes=meta,
                    created_at=r.discovered_at or now,
                    last_seen=r.discovered_at or now,
                )
            else:
                existing = nodes_map[canon_id]
                existing.last_seen = max(existing.last_seen, r.discovered_at or now)
                existing.attributes.update(meta)

            if r.provenance and r.provenance.immutable_hash:
                nodes_map[canon_id].provenance_ids.append(r.provenance.immutable_hash)

            # Create or update edge from root to discovered node
            edge_key = f"{root_canon}->{canon_id}"
            is_verified = "#status/verified" in r.tags or (r.provenance and r.provenance.verification_level != "Unverified/Anecdotal")
            if edge_key not in edges_map:
                w = GraphWeightEngine.compute_edge_weight(1, base_confidence=r.confidence_score, is_verified=is_verified)
                edges_map[edge_key] = EntityEdge(
                    edge_id=edge_key,
                    source_id=root_canon,
                    target_id=canon_id,
                    relation_type="owns" if r.entity_type in ("social_profile", "username") else "associated_with",
                    weight=w,
                    first_seen=r.discovered_at or now,
                    last_seen=r.discovered_at or now,
                    evidence_count=1,
                )
            else:
                e = edges_map[edge_key]
                e.evidence_count += 1
                e.last_seen = max(e.last_seen, r.discovered_at or now)
                e.weight = GraphWeightEngine.compute_edge_weight(
                    e.evidence_count, base_confidence=r.confidence_score, is_verified=is_verified, relation_type=e.relation_type
                )

        return list(nodes_map.values()), list(edges_map.values())
