"""RiskScoringEngine implementing IRiskScoringEngine with automated rule evaluation and report generation."""

from datetime import datetime, timezone
from typing import List, Optional
from ariadne.core.interfaces import IRiskScoringEngine, ILogger
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.risk.models import RiskAssessment, RiskIndicator, RiskLevel
from ariadne.risk.rules.base import BaseRiskRule
from ariadne.risk.rules.builtin import (
    CredentialLeakRule,
    CrossPlatformExposureRule,
    SuspiciousDomainRegistrationRule,
    UnprotectedSocialBioRule,
)


class RiskScoringEngine(IRiskScoringEngine):
    """Central risk scoring engine running pluggable rules and computing normalized risk assessments."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        self.logger = logger
        self.rules: List[BaseRiskRule] = [
            CredentialLeakRule(),
            CrossPlatformExposureRule(),
            SuspiciousDomainRegistrationRule(),
            UnprotectedSocialBioRule(),
        ]

    def register_rule(self, rule: BaseRiskRule) -> None:
        """Register a custom risk evaluation rule."""
        self.rules.append(rule)

    def assess_risk(self, target: TargetEntity, results: List[IntelligenceResult]) -> RiskAssessment:
        """Run all registered risk rules across intelligence findings and compute total risk score [0-100]."""
        indicators: List[RiskIndicator] = []
        total_score = 0.0

        for rule in self.rules:
            try:
                ind = rule.evaluate(target, results)
                if ind:
                    indicators.append(ind)
                    total_score += ind.score_contribution
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error evaluating risk rule {rule.rule_id}: {e}")

        normalized_score = round(min(100.0, max(0.0, total_score)), 1)
        if normalized_score >= 80.0:
            level = RiskLevel.CRITICAL
        elif normalized_score >= 60.0:
            level = RiskLevel.HIGH
        elif normalized_score >= 40.0:
            level = RiskLevel.MEDIUM
        elif normalized_score >= 20.0:
            level = RiskLevel.LOW
        else:
            level = RiskLevel.INFO

        summary = self.format_markdown_summary(target, normalized_score, level, indicators)
        return RiskAssessment(
            target_id=target.target_id,
            overall_score=normalized_score,
            overall_level=level,
            indicators=indicators,
            assessed_at=datetime.now(timezone.utc),
            summary_markdown=summary,
        )

    def format_markdown_summary(
        self,
        target: TargetEntity,
        score: float,
        level: RiskLevel,
        indicators: List[RiskIndicator],
    ) -> str:
        """Format risk assessment breakdown into markdown."""
        color_icon = "🔴" if level in (RiskLevel.CRITICAL, RiskLevel.HIGH) else ("🟡" if level == RiskLevel.MEDIUM else "🟢")
        lines = [
            f"### {color_icon} Security Risk Assessment (`{target.display_name}`)",
            f"**Normalized Risk Score:** `{score}/100` (`{level.value}` Severity)",
            "",
            "#### Triggered Risk Indicators Table",
            "| Rule / Exposure Title | Severity | Score Impact | Remediation Advice |",
            "| :--- | :--- | :--- | :--- |",
        ]

        if not indicators:
            lines.append("| *No risk exposures detected* | `INFO` | `+0` | Continue regular monitoring |")
        else:
            for ind in indicators:
                lines.append(f"| **{ind.title}** | `{ind.severity.value}` | `+{ind.score_contribution:.0f}` | {ind.remediation} |")

        return "\n".join(lines)
