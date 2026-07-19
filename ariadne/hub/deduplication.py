"""HubDeduplicationManager merging duplicate findings and retaining highest confidence scores."""

from typing import Dict, List, Optional
from ariadne.core.interfaces import ILogger
from ariadne.core.models import IntelligenceResult


class HubDeduplicationManager:
    """Deduplicates intelligence findings by URL and semantic keys, merging metadata and confidence scores."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        """Initialize HubDeduplicationManager."""
        self.logger = logger

    @staticmethod
    def _make_signature(result: IntelligenceResult) -> str:
        url = getattr(result, "url", "") or ""
        if url:
            return f"url:{url.strip().lower()}"
        return f"title:{result.title.strip().lower()}|{result.entity_type}"

    def deduplicate(self, results: List[IntelligenceResult]) -> List[IntelligenceResult]:
        """Merge identical results, keeping the highest confidence score and combined tags/links."""
        if not results:
            return []

        deduped: Dict[str, IntelligenceResult] = {}
        for res in results:
            sig = self._make_signature(res)
            if sig not in deduped:
                deduped[sig] = res
            else:
                existing = deduped[sig]
                # Merge tags and links
                merged_tags = list(set(existing.tags + res.tags))
                merged_links = list(set(existing.links_to + res.links_to))
                # Retain highest confidence score
                best_conf = max(existing.confidence_score, res.confidence_score)
                # Retain existing object with updated fields
                existing.tags = merged_tags
                existing.links_to = merged_links
                existing.confidence_score = best_conf

        final_list = list(deduped.values())
        if self.logger and len(final_list) < len(results):
            self.logger.info(
                f"[HubDeduplication] Deduplicated {len(results)} findings into {len(final_list)} unique results"
            )
        return final_list
