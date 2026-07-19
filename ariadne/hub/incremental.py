"""IncrementalScanEngine calculating delta intelligence between previous and current scans."""

from typing import Dict, List, Optional, Set, Tuple
from ariadne.core.interfaces import ILogger
from ariadne.core.models import IntelligenceResult


class IncrementalScanEngine:
    """Computes delta findings across intelligence scans for differential reporting."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        """Initialize IncrementalScanEngine."""
        self.logger = logger

    @staticmethod
    def _get_item_signature(item: IntelligenceResult) -> str:
        url = getattr(item, "url", "") or ""
        return f"{item.title.strip().lower()}|{url.strip().lower()}|{item.entity_type}"

    def compute_delta(
        self,
        previous_results: List[IntelligenceResult],
        current_results: List[IntelligenceResult],
    ) -> Tuple[List[IntelligenceResult], List[IntelligenceResult], int]:
        """Compare previous and current results.

        Returns:
            (new_findings, updated_findings, unchanged_count)
        """
        prev_map: Dict[str, IntelligenceResult] = {
            self._get_item_signature(r): r for r in previous_results
        }

        new_findings: List[IntelligenceResult] = []
        updated_findings: List[IntelligenceResult] = []
        unchanged_count = 0

        for cur in current_results:
            sig = self._get_item_signature(cur)
            if sig not in prev_map:
                new_findings.append(cur)
            else:
                prev = prev_map[sig]
                # Check if confidence score or content changed meaningfully
                if (
                    abs(cur.confidence_score - prev.confidence_score) > 0.05
                    or cur.content_markdown != prev.content_markdown
                    or cur.metadata != prev.metadata
                ):
                    updated_findings.append(cur)
                else:
                    unchanged_count += 1

        if self.logger:
            self.logger.info(
                f"[IncrementalScan] Delta computed: {len(new_findings)} new, {len(updated_findings)} updated, {unchanged_count} unchanged"
            )

        return new_findings, updated_findings, unchanged_count
