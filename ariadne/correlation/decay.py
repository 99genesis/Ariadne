"""TimeDecayCalculator calculating intelligence reliability over time using half-life decay curves."""

import math
from datetime import datetime, timezone
from typing import Dict


class TimeDecayCalculator:
    """Calculates time-decayed confidence scores based on entity-specific half-life formulas."""

    # Half-life in seconds by entity type
    DEFAULT_HALF_LIVES: Dict[str, float] = {
        "ip": 30.0 * 86400.0,            # 30 days
        "location": 90.0 * 86400.0,      # 90 days
        "geo": 90.0 * 86400.0,           # 90 days
        "phone": 365.0 * 86400.0,        # 1 year
        "email": 365.0 * 86400.0,        # 1 year
        "social_profile": 730.0 * 86400.0,  # 2 years
        "username": 730.0 * 86400.0,     # 2 years
        "domain": 730.0 * 86400.0,       # 2 years
    }

    @classmethod
    def calculate_decayed_score(
        cls,
        initial_confidence: float,
        discovered_at: datetime,
        entity_type: str,
        current_time: datetime = None,
    ) -> float:
        """Apply exponential half-life decay formula: C(t) = C_0 * 0.5^(t / T_half)."""
        now = current_time or datetime.now(timezone.utc)
        if discovered_at.tzinfo is None:
            discovered_at = discovered_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        elapsed_seconds = max(0.0, (now - discovered_at).total_seconds())
        half_life = cls.DEFAULT_HALF_LIVES.get(entity_type.lower(), 365.0 * 86400.0)

        # C(t) = C_0 * 0.5^(t / T_half)
        decay_factor = math.pow(0.5, elapsed_seconds / half_life)
        decayed = initial_confidence * decay_factor
        return round(max(0.0, min(1.0, decayed)), 4)
