"""Username Intelligence Plugin implementing IPlugin with dynamic platform discovery and identity correlation."""

import asyncio
from typing import Any, Dict, List
import aiohttp

from ariadne.core.interfaces import IEventBus, IPlugin, IProvider
from ariadne.core.models import IntelligenceResult, TargetEntity, TargetType
from ariadne.events.topics import UsernameFoundEvent
from ariadne.plugins.builtin.username_intel.correlation import IdentityScorer
from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile
from ariadne.plugins.builtin.username_intel.registry import UsernameProviderRegistry


class UsernameIntelPlugin(IPlugin):
    """Executes rate-limited username intelligence across 30+ platform providers and correlates identity."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.event_bus: IEventBus | None = None
        self.registry = UsernameProviderRegistry()

    @property
    def plugin_id(self) -> str:
        return "ariadne.builtin.username_intel"

    async def initialize(self, config: Dict[str, Any], event_bus: IEventBus) -> bool:
        self.config = config
        self.event_bus = event_bus
        # Discover all built-in username platform providers dynamically
        self.registry.discover()
        return True

    async def can_handle(self, target: TargetEntity) -> bool:
        return target.target_type in (TargetType.USERNAME, TargetType.PERSON) or "username" in target.metadata

    async def execute(self, target: TargetEntity, providers: Dict[str, IProvider]) -> List[IntelligenceResult]:
        username = target.metadata.get("username", target.display_name).strip().replace("@", "")
        if not username:
            return []

        active_providers = self.registry.list_providers(enabled_only=True)
        if not active_providers:
            return []

        timeout = aiohttp.ClientTimeout(total=20)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Ariadne/1.2"
        }

        discovered_profiles: List[BaseUsernameProfile] = []

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            tasks = [provider.check_profile(session, username) for provider in active_providers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for p in results:
                if isinstance(p, BaseUsernameProfile) and p.is_present:
                    discovered_profiles.append(p)
                    if self.event_bus:
                        await self.event_bus.publish(
                            UsernameFoundEvent(
                                target_id=target.target_id,
                                platform=p.platform_name,
                                username=p.username,
                                profile_url=p.profile_url,
                                avatar_url=p.avatar_url,
                            )
                        )

        if not discovered_profiles:
            return []

        # Calculate correlation score and details across all findings
        overall_score, correlation_details = IdentityScorer.calculate_score(username, discovered_profiles)

        intel_results: List[IntelligenceResult] = []

        # 1. Create individual IntelligenceResult for each positive profile
        for p in discovered_profiles:
            tags = [
                f"#platform/{p.platform_name.lower()}",
                f"#category/{p.category.lower()}",
                "#osint/username",
                "#status/verified",
            ]
            if p.is_verified:
                tags.append("#badge/verified")

            content = (
                f"### Verified {p.platform_name} Account\n\n"
                f"- **Username:** `{p.username}`\n"
                f"- **Category:** `{p.category.upper()}`\n"
                f"- **Profile Link:** [Visit Profile]({p.profile_url})\n"
                f"- **Confidence Score:** {p.confidence_score * 100:.1f}%\n"
            )
            if p.display_name:
                content += f"- **Display Name:** {p.display_name}\n"
            if p.bio:
                content += f"- **Bio / Summary:** {p.bio}\n"
            if p.created_at:
                content += f"- **Created At:** {p.created_at}\n"

            intel_results.append(
                IntelligenceResult(
                    title=f"{p.platform_name} Profil Bulgusu: @{p.username}",
                    entity_type=f"{p.category}_profile",
                    source_plugin=self.plugin_id,
                    confidence_score=p.confidence_score,
                    tags=tags,
                    links_to=[f"[[Platform_{p.platform_name}]]", f"[[User_{p.username}]]"],
                    metadata=p.model_dump(),
                    content_markdown=content,
                )
            )

        # 2. Create Master Correlation Report Note
        score_bar = IdentityScorer.format_score_bar(overall_score)
        cross_links_md = "\n".join(f"  • {link}" for link in correlation_details["cross_links_found"]) or "  • None detected"
        profiles_list_md = "\n".join(
            f"  • **{p.platform_name}** (`{p.category.upper()}`): [{p.profile_url}]({p.profile_url})"
            for p in discovered_profiles
        )

        master_content = (
            f"## Identity Correlation Report: @{username}\n\n"
            f"- **Overall Identity Match Score:** {overall_score * 100:.0f}% ({score_bar})\n"
            f"- **Total Platforms Checked:** {len(active_providers)}\n"
            f"- **Verified Profiles Found:** {len(discovered_profiles)}\n\n"
            f"### Key Correlation Indicators\n"
            f"- Exact Username Matches: `{correlation_details['exact_matches']}`\n"
            f"- Display Name Similarity Matches: `{correlation_details['display_name_matches']}`\n"
            f"- Shared Avatar / Icon Matches: `{correlation_details['avatar_matches']}`\n"
            f"- Platform Verification Badges: `{correlation_details['verified_profiles']}`\n\n"
            f"### Cross-Platform Links Detected in Bios\n{cross_links_md}\n\n"
            f"### Discovered Profiles Summary\n{profiles_list_md}\n"
        )

        intel_results.append(
            IntelligenceResult(
                title=f"Kimlik Korelasyon Analizi (Identity Correlation): @{username}",
                entity_type="identity_correlation",
                source_plugin=self.plugin_id,
                confidence_score=overall_score,
                tags=["#osint/identity_correlation", f"#target/{username.lower()}", "#summary/master"],
                links_to=[f"[[User_{username}]]"] + [f"[[Platform_{p.platform_name}]]" for p in discovered_profiles],
                metadata=correlation_details,
                content_markdown=master_content,
            )
        )

        return intel_results

    async def cleanup(self) -> None:
        pass


def get_plugin() -> IPlugin:
    return UsernameIntelPlugin()
