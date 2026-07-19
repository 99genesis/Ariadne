"""Identity Correlation Engine (`IdentityScorer`) for Username Intelligence.

Cross-compares discovered platform profiles across display names, bio cross-links,
avatar URLs, and category overlap to compute an overall probability that the findings
belong to the exact same human/entity identity.
"""

import difflib
import re
from typing import Any, Dict, List, Tuple

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile


class IdentityScorer:
    """Computes identity correlation scores and cross-link matching across profiles."""

    @classmethod
    def calculate_score(cls, target_username: str, profiles: List[BaseUsernameProfile]) -> Tuple[float, Dict[str, Any]]:
        """Calculate overall correlation probability score [0.0 - 1.0] and detailed breakdown.

        Args:
            target_username: Target handle queried.
            profiles: List of positive profile findings discovered.

        Returns:
            Tuple of (overall_score, correlation_details_dict).
        """
        if not profiles:
            return 0.0, {"reasons": ["No positive profiles discovered."], "exact_matches": 0, "cross_links": []}

        clean_target = target_username.strip().lower()
        exact_matches = 0
        display_name_matches = 0
        avatar_matches = 0
        cross_links_found: List[str] = []
        verified_count = 0

        avatar_urls = set()
        all_bios = []

        for p in profiles:
            p_user_clean = p.username.strip().lower()
            if p_user_clean == clean_target:
                exact_matches += 1

            if p.is_verified:
                verified_count += 1

            # Check display name similarity
            if p.display_name:
                sim = difflib.SequenceMatcher(None, clean_target, p.display_name.strip().lower()).ratio()
                if sim >= 0.6 or clean_target in p.display_name.strip().lower():
                    display_name_matches += 1

            # Check avatars
            if p.avatar_url and "default" not in p.avatar_url.lower():
                if p.avatar_url in avatar_urls:
                    avatar_matches += 1
                avatar_urls.add(p.avatar_url)

            # Collect bios for cross-link correlation
            if p.bio:
                all_bios.append((p.platform_name, p.bio))

        # Check cross-links inside bios (e.g., bio mentioning twitter.com/handle or github.com/handle)
        for platform_source, bio_text in all_bios:
            for p_target in profiles:
                if p_target.platform_name != platform_source:
                    p_url_domain = p_target.profile_url.replace("https://", "").replace("http://", "").rstrip("/")
                    if p_url_domain.lower() in bio_text.lower() or f"@{clean_target}" in bio_text.lower():
                        link_info = f"{platform_source} bio links to {p_target.platform_name} ({clean_target})"
                        if link_info not in cross_links_found:
                            cross_links_found.append(link_info)

        # Base score starts with ratio of exact username matches and profile count
        base_score = min(0.50, (exact_matches * 0.15))

        # Boosts
        if len(profiles) >= 3:
            base_score += 0.15
        elif len(profiles) >= 2:
            base_score += 0.10

        if display_name_matches >= 2:
            base_score += 0.15
        elif display_name_matches == 1:
            base_score += 0.08

        if avatar_matches >= 1:
            base_score += 0.15

        if cross_links_found:
            base_score += min(0.25, len(cross_links_found) * 0.15)

        if verified_count > 0:
            base_score += 0.10

        final_score = min(1.0, max(0.10 if profiles else 0.0, base_score))

        details = {
            "target_username": target_username,
            "total_profiles_found": len(profiles),
            "exact_matches": exact_matches,
            "display_name_matches": display_name_matches,
            "avatar_matches": avatar_matches,
            "verified_profiles": verified_count,
            "cross_links_found": cross_links_found,
            "overall_score": final_score,
            "score_percentage": f"{final_score * 100:.0f}%",
        }
        try:
            from ariadne.correlation.xai import ExplainableAIFormatter
            details["explanation_markdown"] = ExplainableAIFormatter.explain_correlation(final_score, details)
        except Exception:
            pass
        return final_score, details

    @classmethod
    def format_score_bar(cls, score: float) -> str:
        """Render rich progress bar representation of correlation score e.g. ██████████ 92%."""
        percentage = int(score * 100)
        filled_blocks = round(score * 10)
        empty_blocks = 10 - filled_blocks
        bar = ("█" * filled_blocks) + ("░" * empty_blocks)
        color = "green" if score >= 0.75 else ("yellow" if score >= 0.45 else "red")
        return f"[{color}]{bar} {percentage}%[/{color}]"
