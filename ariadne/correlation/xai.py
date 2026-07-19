"""ExplainableAIFormatter producing transparent, human-readable rationales for correlation decisions."""

from typing import Any, Dict


class ExplainableAIFormatter:
    """Generates human-readable breakdowns and markdown reports explaining correlation decisions."""

    @staticmethod
    def explain_correlation(score: float, details: Dict[str, Any]) -> str:
        """Produce a structured markdown explanation of the correlation score and underlying evidence."""
        pct = int(score * 100)
        target = details.get("target_username") or details.get("target_id", "Unknown")
        exact = details.get("exact_matches", 0)
        disp = details.get("display_name_matches", 0)
        avatars = details.get("avatar_matches", 0)
        verified = details.get("verified_profiles", 0)
        links = details.get("cross_links_found", [])

        lines = [
            f"### Explainable AI Correlation Assessment (`{target}`)",
            f"**Overall Probability:** `{pct}%` (Score: `{score:.2f}`)",
            "",
            "#### Evidence Breakdown Table",
            "| Dimension | Count / Status | Impact on Score |",
            "| :--- | :--- | :--- |",
            f"| Exact Handle Matches | `{exact}` | Base contribution up to 50% |",
            f"| Display Name Similarity | `{disp}` | +8% to +15% boost |",
            f"| Avatar Reuse Across Sites | `{avatars}` | +15% boost if shared |",
            f"| Verified Platform Badges | `{verified}` | +10% trust multiplier |",
            f"| Cross-Platform Bio Links | `{len(links)}` | +15% per link (max +25%) |",
            "",
            "#### Key Observations & Provenance",
        ]

        if links:
            lines.append("- **Explicit Cross-Links Found:**")
            for link_str in links:
                lines.append(f"  - `{link_str}`")
        else:
            lines.append("- *No explicit bio cross-links detected across platforms.*")

        if score >= 0.85:
            lines.append("\n**Conclusion:** High convergence across multiple independent indicators confirms identity match.")
        elif score >= 0.50:
            lines.append("\n**Conclusion:** Moderate correlation. Additional OSINT cross-referencing recommended.")
        else:
            lines.append("\n**Conclusion:** Low confidence or isolated finding. Unlikely to share identical identity without further proof.")

        return "\n".join(lines)
