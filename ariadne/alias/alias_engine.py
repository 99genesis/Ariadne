"""CrossPlatformAliasEngine mapping candidate usernames across platforms and domain variations."""

from typing import Any, Dict, List, Optional, Set
from ariadne.core.interfaces import ILogger
from ariadne.core.models import TargetEntity, TargetType
from ariadne.alias.mutation_engine import UsernameMutationEngine


class CrossPlatformAliasEngine:
    """Pre-processes username targets into cross-platform alias variations and platform-specific formats."""

    def __init__(self, mutation_engine: Optional[UsernameMutationEngine] = None, logger: Optional[ILogger] = None) -> None:
        """Initialize CrossPlatformAliasEngine with optional mutation engine delegate."""
        self.mutation_engine = mutation_engine or UsernameMutationEngine(logger=logger)
        self.logger = logger

    def generate_aliases(self, username: str) -> List[Dict[str, Any]]:
        """Generate platform handle variations and domain handles for a base username."""
        clean = username.strip().lower()
        if not clean:
            return []

        # Start with linguistic mutations
        mutations = self.mutation_engine.generate_mutations(clean, max_results=25)

        aliases: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        for mut in mutations:
            uname = mut["username"]
            if uname not in seen:
                seen.add(uname)
                aliases.append({
                    "alias": uname,
                    "platform_hint": "universal",
                    "mutation_type": mut["mutation_type"],
                    "confidence_prior": mut["confidence_prior"],
                })

        # Add platform-specific handle adjustments
        platform_patterns = [
            ("twitter", f"@{clean}"),
            ("instagram", clean),
            ("telegram", clean),
            ("github", clean),
            ("domain", f"{clean.replace('_', '').replace('-', '')}.com"),
            ("domain_dev", f"{clean.replace('_', '').replace('-', '')}.dev"),
        ]

        for plat, handle in platform_patterns:
            if handle not in seen:
                seen.add(handle)
                aliases.append({
                    "alias": handle,
                    "platform_hint": plat,
                    "mutation_type": f"platform_{plat}",
                    "confidence_prior": 0.85 if plat.startswith("domain") else 0.95,
                })

        return aliases

    def expand_target(self, target: TargetEntity, include_mutations: bool = True) -> List[TargetEntity]:
        """Expand a TargetEntity into a comprehensive list of candidate variations."""
        if not include_mutations:
            return [target]

        base = target.display_name if target.target_type == TargetType.USERNAME else target.target_id
        aliases = self.generate_aliases(base)

        entities: List[TargetEntity] = []
        for alias_info in aliases:
            alias_str = alias_info["alias"]
            meta = dict(target.metadata)
            meta.update({
                "alias_hint": alias_str,
                "platform_hint": alias_info["platform_hint"],
                "mutation_type": alias_info["mutation_type"],
                "confidence_prior": alias_info["confidence_prior"],
                "original_target_id": target.target_id,
            })
            t_id = target.target_id if alias_str == base else f"{target.target_id}_{alias_str}"
            entities.append(
                TargetEntity(
                    target_id=t_id,
                    target_type=TargetType.USERNAME,
                    display_name=alias_str,
                    metadata=meta,
                )
            )
        return entities
