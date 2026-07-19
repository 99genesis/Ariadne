"""SourcePriorityManager implementing 7-Tier source hierarchy and early exit checks."""

from typing import Dict, List, Optional
from ariadne.core.interfaces import ILogger
from ariadne.core.models import IntelligenceResult


class SourcePriorityManager:
    """Manages source credibility hierarchy (Tiers 1-7) and early exit heuristics."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        """Initialize priority manager and mapping tables."""
        self.logger = logger
        # Default tier mapping by provider/module substring or exact ID
        self._tier_scores: Dict[str, int] = {
            "official_api": 100,  # Tier 1
            "direct_auth": 100,   # Tier 1
            "google_ai": 60,      # Tier 5 (LLM)
            "openai": 60,         # Tier 5 (LLM)
            "openrouter": 60,     # Tier 5 (LLM)
            "ollama": 60,         # Tier 5 (LLM)
            "dns": 80,            # Tier 3
            "whois": 80,          # Tier 3
            "social_graph": 70,   # Tier 4
            "sherlock": 70,       # Tier 4
            "heuristic": 50,      # Tier 6
            "aggregator": 40,     # Tier 7
        }

    def get_tier_score(self, source_module: Optional[str], provider_id: Optional[str]) -> int:
        """Determine numeric credibility score (100 highest -> 40 lowest) based on tier mapping."""
        for name in (provider_id, source_module):
            if not name:
                continue
            name_lower = str(name).lower()
            for key, score in self._tier_scores.items():
                if key in name_lower:
                    return score
        return 50  # Default Tier 6 heuristic score if unknown

    def sort_by_priority(self, results: List[IntelligenceResult]) -> List[IntelligenceResult]:
        """Sort intelligence findings descending by tier priority and confidence score."""
        return sorted(
            results,
            key=lambda r: (
                self.get_tier_score(r.source_plugin, getattr(r, "provider_used", None)),
                r.confidence_score,
            ),
            reverse=True,
        )

    def should_early_exit(self, current_results: List[IntelligenceResult], confidence_threshold: float = 0.95) -> bool:
        """Evaluate whether high-confidence Tier 1/2 results exist to justify early termination."""
        if not current_results:
            return False
        for res in current_results:
            score = self.get_tier_score(res.source_plugin, getattr(res, "provider_used", None))
            if score >= 90 and res.confidence_score >= confidence_threshold:
                if self.logger:
                    self.logger.info(
                        f"[PriorityManager] Early exit condition met by result '{res.title}' (Score={score}, Conf={res.confidence_score})"
                    )
                return True
        return False
