"""Pydantic domain models representing synthesized Master Intelligence Reports."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ariadne.core.models import IntelligenceResult, TargetEntity


class MasterIntelligenceReport(BaseModel):
    """Synthesized master intelligence report incorporating correlation, risk, timeline, and graph topology."""

    report_id: str = Field(..., description="Report unique ID e.g. report:target:20260718")
    target: TargetEntity = Field(..., description="Target entity investigated")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    results: List[IntelligenceResult] = Field(default_factory=list, description="Verified intelligence items")
    fusion_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall identity fusion score [0.0-1.0]")
    correlation_details: Dict[str, Any] = Field(default_factory=dict, description="Correlation breakdown")
    risk_assessment: Optional[Any] = Field(default=None, description="RiskAssessment object")
    timeline: Optional[Any] = Field(default=None, description="TargetTimeline object")
    graph_snapshot: Optional[Any] = Field(default=None, description="GraphSnapshot object")
    executive_summary: str = Field(default="", description="High-level narrative synthesis")
    master_markdown: str = Field(default="", description="Complete formatted markdown report")
