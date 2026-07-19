"""Relationship Builder determining link connections across findings."""

from typing import List, Set
from ariadne.core.models import IntelligenceResult, TargetEntity


class RelationshipBuilder:
    """Analyzes intelligence findings and builds cross-note relationship links."""

    @classmethod
    def infer_relationships(cls, result: IntelligenceResult, target: TargetEntity) -> List[str]:
        """Infer relationship links such as belongs_to, discovered_via, and colocated.

        Args:
            result: Intelligence result item.
            target: Parent target entity.

        Returns:
            List of double bracket link strings.
        """
        links: Set[str] = set(result.links_to)
        links.add(f"[[{target.target_id}]]")

        # Check for location relationships
        tech = result.metadata or {}
        if "city_guess" in tech and tech["city_guess"] and tech["city_guess"] != "Unknown":
            clean_city = str(tech["city_guess"]).replace(" ", "_").replace("/", "_")
            links.add(f"[[Location_{clean_city}]]")

        if "phone" in tech and tech["phone"]:
            links.add(f"[[Phone_{tech['phone']}]]")

        if "username" in tech and tech["username"]:
            links.add(f"[[User_{tech['username']}]]")

        return sorted(list(links))
