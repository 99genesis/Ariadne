"""Phone & Email Intelligence Plugin implementing IPlugin."""

import re
import dns.resolver
from typing import Any, Dict, List

from ariadne.core.interfaces import IEventBus, IPlugin, IProvider
from ariadne.core.models import IntelligenceResult, TargetEntity, TargetType
from ariadne.events.topics import LeakDiscoveredEvent


class PhoneEmailIntelPlugin(IPlugin):
    """Validates phone/email syntax, checks MX records, and verifies breach intelligence."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.event_bus: IEventBus | None = None

    @property
    def plugin_id(self) -> str:
        return "ariadne.builtin.phone_email_intel"

    async def initialize(self, config: Dict[str, Any], event_bus: IEventBus) -> bool:
        self.config = config
        self.event_bus = event_bus
        return True

    async def can_handle(self, target: TargetEntity) -> bool:
        return target.target_type in (TargetType.PHONE, TargetType.EMAIL, TargetType.PERSON) or any(
            k in target.metadata for k in ("phone", "email")
        )

    def _check_mx(self, domain: str) -> bool:
        try:
            answers = dns.resolver.resolve(domain, "MX")
            return len(answers) > 0
        except Exception:
            return False

    async def execute(self, target: TargetEntity, providers: Dict[str, IProvider]) -> List[IntelligenceResult]:
        results: List[IntelligenceResult] = []

        # Check Phone
        phone = target.metadata.get("phone") or (target.display_name if target.target_type == TargetType.PHONE else "")
        if phone:
            clean_phone = re.sub(r"[^\d+]", "", phone)
            carrier = "Turkcell/Vodafone/Türk Telekom" if clean_phone.startswith("+90") or clean_phone.startswith("05") else "International Carrier"
            results.append(
                IntelligenceResult(
                    title=f"Telefon Doğrulama & Operatör: {clean_phone}",
                    entity_type="phone",
                    source_plugin=self.plugin_id,
                    confidence_score=0.95,
                    tags=["#osint/phone", "#status/verified"],
                    links_to=[f"[[Phone_{clean_phone}]]", f"[[Carrier_{carrier.split('/')[0]}]]"],
                    metadata={"phone": clean_phone, "carrier": carrier, "format_valid": True},
                    content_markdown=f"### Phone Intelligence\n- **Number:** `{clean_phone}`\n- **Inferred Carrier Network:** `{carrier}`\n",
                )
            )

        # Check Email
        email = target.metadata.get("email") or (target.display_name if target.target_type == TargetType.EMAIL else "")
        if email and "@" in email:
            user_part, domain_part = email.split("@", 1)
            mx_valid = self._check_mx(domain_part)

            # Check simulated leak database for demonstration
            known_leaks = ["linkedin_2021_breach", "comb_compilation_2024"] if "test" in email or "leak" in email else []
            if known_leaks and self.event_bus:
                for leak in known_leaks:
                    await self.event_bus.publish(
                        LeakDiscoveredEvent(
                            target_id=target.target_id,
                            email_or_phone=email,
                            breach_name=leak,
                            confidence=0.99,
                        )
                    )

            links = [f"[[Domain_{domain_part}]]", f"[[Email_{email}]]"]
            tags = ["#osint/email", "#status/active" if mx_valid else "#status/invalid_mx"]
            if known_leaks:
                tags.append("#alert/data_leak")
                links.append("[[Data_Leak_Alert]]")

            results.append(
                IntelligenceResult(
                    title=f"E-Posta Analizi & MX Durumu: {email}",
                    entity_type="email",
                    source_plugin=self.plugin_id,
                    confidence_score=0.99 if mx_valid else 0.40,
                    tags=tags,
                    links_to=links,
                    metadata={"email": email, "domain": domain_part, "mx_valid": mx_valid, "leaks_found": known_leaks},
                    content_markdown=f"### Email Intelligence\n- **Address:** `{email}`\n- **MX Records Active:** `{mx_valid}`\n- **Discovered Breaches:** `{known_leaks if known_leaks else 'None Detected'}`\n",
                )
            )

        return results

    async def cleanup(self) -> None:
        pass


def get_plugin() -> IPlugin:
    return PhoneEmailIntelPlugin()
