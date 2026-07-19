"""Built-in risk evaluation rules for credential leaks, exposure, domain threats, and bios."""

from typing import List, Optional
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.risk.models import RiskIndicator, RiskLevel
from ariadne.risk.rules.base import BaseRiskRule


class CredentialLeakRule(BaseRiskRule):
    """Rule detecting breached accounts, leaked passwords, or data breach hits."""

    def __init__(self) -> None:
        super().__init__("rule:cred_leak", "Data Breach & Credential Leak Exposure")

    def evaluate(self, target: TargetEntity, results: List[IntelligenceResult]) -> Optional[RiskIndicator]:
        breaches = []
        for r in results:
            content_lower = (r.content_markdown or "").lower()
            tags_lower = [t.lower() for t in r.tags]
            if "breach" in content_lower or any("breach" in t or "leak" in t for t in tags_lower):
                breaches.append(r.title)

        if breaches:
            return RiskIndicator(
                rule_id=self.rule_id,
                title=self.title,
                description=f"Target identity appeared in {len(breaches)} known data breaches or leaks ({', '.join(breaches[:3])}).",
                severity=RiskLevel.CRITICAL if len(breaches) >= 2 else RiskLevel.HIGH,
                score_contribution=40.0 if len(breaches) >= 2 else 25.0,
                evidence_sources=breaches,
                remediation="Immediately rotate passwords across affected platforms and enable hardware MFA.",
            )
        return None


class CrossPlatformExposureRule(BaseRiskRule):
    """Rule detecting broad digital footprint footprint across numerous public services."""

    def __init__(self) -> None:
        super().__init__("rule:broad_exposure", "High Public Footprint & Multi-Platform Exposure")

    def evaluate(self, target: TargetEntity, results: List[IntelligenceResult]) -> Optional[RiskIndicator]:
        profiles = [r for r in results if r.entity_type in ("social_profile", "social", "username")]
        if len(profiles) >= 6:
            return RiskIndicator(
                rule_id=self.rule_id,
                title=self.title,
                description=f"Target has active profiles across {len(profiles)} public platforms, increasing attack surface.",
                severity=RiskLevel.MEDIUM,
                score_contribution=20.0,
                evidence_sources=[r.title for r in profiles[:5]],
                remediation="Audit public profile visibility settings and remove abandoned accounts.",
            )
        return None


class SuspiciousDomainRegistrationRule(BaseRiskRule):
    """Rule detecting malicious domain flags, phishing tags, or threat intel hits."""

    def __init__(self) -> None:
        super().__init__("rule:suspicious_domain", "Threat Intelligence Flag on Infrastructure")

    def evaluate(self, target: TargetEntity, results: List[IntelligenceResult]) -> Optional[RiskIndicator]:
        threats = []
        for r in results:
            tags_lower = [t.lower() for t in r.tags]
            if any("malware" in t or "phishing" in t or "threat" in t for t in tags_lower):
                threats.append(r.title)

        if threats:
            return RiskIndicator(
                rule_id=self.rule_id,
                title=self.title,
                description=f"Infrastructure associated with target flagged for malicious activities ({', '.join(threats)}).",
                severity=RiskLevel.CRITICAL,
                score_contribution=45.0,
                evidence_sources=threats,
                remediation="Quarantine infrastructure and inspect DNS/TLS logs for compromise.",
            )
        return None


class UnprotectedSocialBioRule(BaseRiskRule):
    """Rule detecting sensitive personal contact details exposed inside open social bios."""

    def __init__(self) -> None:
        super().__init__("rule:bio_exposure", "Open Contact PII Exposure in Profile Bio")

    def evaluate(self, target: TargetEntity, results: List[IntelligenceResult]) -> Optional[RiskIndicator]:
        exposed = []
        for r in results:
            bio = (r.metadata or {}).get("bio", r.content_markdown or "")
            if "@" in bio and ("." in bio or "email" in bio.lower() or "telegram" in bio.lower() or "t.me/" in bio.lower()):
                exposed.append(r.title)

        if exposed:
            return RiskIndicator(
                rule_id=self.rule_id,
                title=self.title,
                description=f"Direct contact details or chat links exposed plainly in public bios ({', '.join(exposed)}).",
                severity=RiskLevel.LOW,
                score_contribution=10.0,
                evidence_sources=exposed,
                remediation="Remove direct email/phone numbers from public bios to prevent targeted social engineering.",
            )
        return None
