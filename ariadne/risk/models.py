"""Pydantic domain models for Risk Scoring Engine."""

from datetime import datetime, timezone
from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Categorical risk severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class RiskIndicator(BaseModel):
    """Specific vulnerability or security exposure finding contributing to the overall risk score."""

    rule_id: str = Field(..., description="Unique rule identifier e.g. rule:cred_leak")
    title: str = Field(..., description="Short title of the indicator")
    description: str = Field(..., description="Detailed explanation of the risk exposure")
    severity: RiskLevel = Field(default=RiskLevel.MEDIUM)
    score_contribution: float = Field(default=15.0, ge=0.0, le=100.0, description="Score impact [0-100]")
    evidence_sources: List[str] = Field(default_factory=list, description="Discoveries triggering this rule")
    remediation: str = Field(default="No specific remediation recommended.", description="Actionable mitigation advice")


class RiskAssessment(BaseModel):
    """Complete aggregated risk assessment report for a target entity."""

    target_id: str = Field(..., description="Target entity ID")
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Normalized risk score [0-100]")
    overall_level: RiskLevel = Field(default=RiskLevel.INFO)
    indicators: List[RiskIndicator] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary_markdown: str = Field(default="", description="Formatted report for terminal and Obsidian")
