"""Metadata Builder for enriching frontmatter dictionaries."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ariadne.core.models import IntelligenceResult, TargetEntity


class MetadataBuilder:
    """Enriches and formats standard metadata fields for YAML frontmatter."""

    @classmethod
    def build_frontmatter(
        self,
        result: IntelligenceResult,
        target: TargetEntity,
        note_id: str,
        additional_links: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Construct standard, enriched frontmatter dictionary.

        Args:
            result: Atomic intelligence finding.
            target: Parent target entity under investigation.
            note_id: Unique note ID.
            additional_links: Optional list of double bracket links.

        Returns:
            Clean dictionary ready for YAML serialization.
        """
        links = set(result.links_to)
        links.add(f"[[{target.target_id}]]")
        if additional_links:
            links.update(additional_links)

        # Standard tags
        tags = set(result.tags)
        tags.add(f"#target/{target.target_type.value if hasattr(target.target_type, 'value') else target.target_type}")
        tags.add(f"#entity/{result.entity_type}")

        fm: Dict[str, Any] = {
            "id": note_id,
            "title": result.title,
            "target_id": target.target_id,
            "entity_type": result.entity_type,
            "source_module": result.source_plugin,
            "confidence_score": round(result.confidence_score, 3),
            "discovered_at": result.discovered_at.isoformat(),
            "tags": sorted(list(tags)),
            "links_to": sorted(list(links)),
        }

        if result.provider_used:
            fm["provider_used"] = result.provider_used

        if result.metadata:
            fm["technical_details"] = result.metadata

        return fm
