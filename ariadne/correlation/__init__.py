"""Correlation Engine 2.0 package for intelligence fusion, provenance, decay, verification, and XAI."""

from ariadne.correlation.provenance import ProvenanceChainBuilder
from ariadne.correlation.decay import TimeDecayCalculator
from ariadne.correlation.verification import EvidenceVerificationEngine
from ariadne.correlation.xai import ExplainableAIFormatter
from ariadne.correlation.engine import CorrelationEngine

__all__ = [
    "ProvenanceChainBuilder",
    "TimeDecayCalculator",
    "EvidenceVerificationEngine",
    "ExplainableAIFormatter",
    "CorrelationEngine",
]
