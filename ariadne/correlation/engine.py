"""CorrelationEngine 2.0 implementing ICorrelationEngine with provenance, time decay, verification, and XAI."""

from typing import Any, Dict, List, Optional, Tuple
from ariadne.core.interfaces import ICorrelationEngine, ILogger
from ariadne.core.models import IntelligenceResult, TargetEntity, TargetType
from ariadne.correlation.decay import TimeDecayCalculator
from ariadne.correlation.provenance import ProvenanceChainBuilder
from ariadne.correlation.verification import EvidenceVerificationEngine
from ariadne.correlation.xai import ExplainableAIFormatter
from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile


class CorrelationEngine(ICorrelationEngine):
    """Central correlation engine fusing multi-source discoveries, computing time decay, and providing explainability."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        """Initialize CorrelationEngine 2.0."""
        self.logger = logger
        self.decay_calc = TimeDecayCalculator()
        self.verification_engine = EvidenceVerificationEngine()
        self.xai_formatter = ExplainableAIFormatter()

    def apply_provenance_and_decay(
        self,
        results: List[IntelligenceResult],
        origin_module: str = "correlation_engine",
    ) -> List[IntelligenceResult]:
        """Attach cryptographic provenance chains and apply half-life decay to confidence scores."""
        processed: List[IntelligenceResult] = []
        for r in results:
            # Apply time decay
            decayed_conf = self.decay_calc.calculate_decayed_score(
                r.confidence_score,
                r.discovered_at,
                r.entity_type,
            )
            r.confidence_score = decayed_conf

            # Build provenance if missing
            if not r.provenance:
                r.provenance = ProvenanceChainBuilder.build_provenance(
                    source_id=getattr(r, "url", "") or r.title,
                    origin_module=r.source_plugin or origin_module,
                    confidence=decayed_conf,
                    payload=r.model_dump(mode="json"),
                )
            processed.append(r)

        # Cross-verify evidence
        return self.verification_engine.verify_evidence(processed)

    def correlate_findings(
        self,
        target: TargetEntity,
        results: List[IntelligenceResult],
    ) -> Tuple[float, Dict[str, Any]]:
        """Correlate a list of intelligence results against the target entity to compute fusion score and details."""
        if not results:
            return 0.0, {"target_id": target.target_id, "reasons": ["No results to correlate."], "overall_score": 0.0}

        processed = self.apply_provenance_and_decay(results)

        # If target is username, convert results to BaseUsernameProfile to leverage IdentityScorer logic
        profiles: List[BaseUsernameProfile] = []
        for r in processed:
            if r.entity_type in ("social_profile", "social", "username"):
                meta = r.metadata or {}
                url_val = (
                    getattr(r, "url", None)
                    or (getattr(r, "__pydantic_extra__", {}) or {}).get("url")
                    or meta.get("url")
                    or meta.get("profile_url")
                    or f"https://{r.source_plugin}/{target.display_name}"
                )
                profiles.append(
                    BaseUsernameProfile(
                        username=meta.get("username", target.display_name),
                        platform_name=meta.get("platform", r.source_plugin),
                        profile_url=url_val,
                        display_name=meta.get("display_name", target.display_name),
                        avatar_url=meta.get("avatar_url", ""),
                        bio=meta.get("bio", r.content_markdown),
                        is_verified=meta.get("is_verified", False),
                    )
                )

        if profiles:
            from ariadne.plugins.builtin.username_intel.correlation import IdentityScorer
            score, details = IdentityScorer.calculate_score(target.display_name, profiles)
        else:
            # General weighted average of confidence scores across verified intelligence items
            score = sum(r.confidence_score for r in processed) / len(processed)
            details = {
                "target_id": target.target_id,
                "total_findings": len(processed),
                "exact_matches": len(processed),
                "overall_score": score,
                "score_percentage": f"{score * 100:.0f}%",
            }

        details["explanation_markdown"] = self.xai_formatter.explain_correlation(score, details)
        return score, details

    def get_explanation(self, score: float, details: Dict[str, Any]) -> str:
        """Return XAI formatted explanation."""
        return self.xai_formatter.explain_correlation(score, details)
