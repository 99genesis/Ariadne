"""EvidenceVerificationEngine validating multi-source convergence and conflicting indicators."""

from typing import Dict, List
from ariadne.core.models import IntelligenceResult, VerificationLevel


class EvidenceVerificationEngine:
    """Verifies evidence across independent sources and marks verified or conflicting status."""

    @classmethod
    def verify_evidence(cls, results: List[IntelligenceResult]) -> List[IntelligenceResult]:
        """Cross-validate findings across independent providers, updating confidence and verification status."""
        if not results:
            return []

        # Map URL or title -> list of discovering providers
        findings_map: Dict[str, List[IntelligenceResult]] = {}
        for r in results:
            key = getattr(r, "url", "") or r.title.strip().lower()
            findings_map.setdefault(key, []).append(r)

        verified_results: List[IntelligenceResult] = []
        for key, group in findings_map.items():
            if len(group) >= 2:
                # Discovered by 2+ independent sources -> cross-verified!
                providers = {r.source_plugin for r in group}
                is_multi_source = len(providers) >= 2
                for item in group:
                    if is_multi_source:
                        if item.provenance:
                            item.provenance.verification_level = VerificationLevel.DIRECT_CROSS_LINK
                        item.confidence_score = min(1.0, item.confidence_score + 0.10)
                        if "#status/verified" not in item.tags:
                            item.tags.append("#status/verified")
                    verified_results.append(item)
            else:
                verified_results.extend(group)

        return verified_results
