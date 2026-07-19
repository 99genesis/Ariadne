"""Base abstract class for risk evaluation rules."""

from abc import ABC, abstractmethod
from typing import List, Optional
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.risk.models import RiskIndicator


class BaseRiskRule(ABC):
    """Abstract base class for all pluggable risk evaluation rules."""

    def __init__(self, rule_id: str, title: str) -> None:
        self.rule_id = rule_id
        self.title = title

    @abstractmethod
    def evaluate(self, target: TargetEntity, results: List[IntelligenceResult]) -> Optional[RiskIndicator]:
        """Evaluate intelligence findings against this rule and return a RiskIndicator if exposed."""
        pass
