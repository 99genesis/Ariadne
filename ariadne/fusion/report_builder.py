"""MasterReportBuilder synthesizing correlation, risk, graph, and timeline into professional reports."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.fusion.models import MasterIntelligenceReport


class MasterReportBuilder:
    """Formats master intelligence synthesis into Obsidian and CLI ready markdown documents."""

    @staticmethod
    def build_master_report(
        target: TargetEntity,
        results: List[IntelligenceResult],
        fusion_score: float,
        correlation_details: Dict[str, Any],
        risk_assessment: Optional[Any] = None,
        timeline: Optional[Any] = None,
        graph_snapshot: Optional[Any] = None,
    ) -> MasterIntelligenceReport:
        """Compile complete Master Intelligence Report and render rich markdown."""
        now = datetime.now(timezone.utc)
        pct = int(fusion_score * 100)

        # Build YAML frontmatter for Obsidian
        tags = ["#osint", "#report", f"#target/{target.target_id}"]
        if risk_assessment and getattr(risk_assessment, "overall_level", None):
            tags.append(f"#risk/{risk_assessment.overall_level.value.lower()}")

        lines = [
            "---",
            f"title: Master Intelligence Report - {target.display_name}",
            f"target_id: {target.target_id}",
            f"target_type: {target.target_type.value}",
            f"date: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"fusion_confidence: {pct}%",
            f"tags: [{', '.join(tags)}]",
            "---",
            "",
            f"# 🎯 Master Intelligence Report: `{target.display_name}`",
            "",
            "## 1. Executive Summary",
            f"Ariadne Intelligence Fusion completed automated analysis across **{len(results)}** verified findings. "
            f"The overall identity correlation convergence is **{pct}%** (`{fusion_score:.2f}`).",
        ]

        if risk_assessment:
            score = getattr(risk_assessment, "overall_score", 0.0)
            level = getattr(risk_assessment, "overall_level", "INFO")
            lvl_str = level.value if hasattr(level, "value") else str(level)
            lines.append(f"The target security exposure index is assessed at **{score}/100** (**{lvl_str}** severity).")

        lines.extend([
            "",
            "## 2. Correlation & Explainable AI Assessment",
            correlation_details.get("explanation_markdown", f"Overall correlation probability: {pct}%."),
            "",
        ])

        if risk_assessment and getattr(risk_assessment, "summary_markdown", ""):
            lines.extend([
                "## 3. Security Risk Exposure",
                risk_assessment.summary_markdown,
                "",
            ])

        if timeline and hasattr(timeline, "events"):
            from ariadne.timeline.generator import TimelineGenerator
            lines.extend([
                "## 4. Chronological Timeline Analysis",
                TimelineGenerator().to_markdown(timeline),
                "",
            ])

        if graph_snapshot and hasattr(graph_snapshot, "nodes"):
            from ariadne.graph.visualizer import GraphVisualizer
            lines.extend([
                "## 5. Entity Relationship Topology",
                f"**Total Nodes:** `{len(graph_snapshot.nodes)}` | **Total Edges:** `{len(graph_snapshot.edges)}`",
                "",
                "```mermaid",
                GraphVisualizer.to_mermaid(graph_snapshot),
                "```",
                "",
            ])

        lines.extend([
            "## 6. Discovered Intelligence Register",
            "| Title | Entity Type | Confidence | Source Plugin | Discovered At |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])

        for r in results:
            ts = r.discovered_at.strftime("%Y-%m-%d %H:%M") if r.discovered_at else "N/A"
            lines.append(f"| **{r.title}** | `{r.entity_type}` | `{r.confidence_score:.2f}` | `{r.source_plugin}` | `{ts}` |")

        master_md = "\n".join(lines)
        return MasterIntelligenceReport(
            report_id=f"report:{target.target_id}:{now.strftime('%Y%m%d%H%M%S')}",
            target=target,
            generated_at=now,
            results=results,
            fusion_score=fusion_score,
            correlation_details=correlation_details,
            risk_assessment=risk_assessment,
            timeline=timeline,
            graph_snapshot=graph_snapshot,
            executive_summary=f"Automated fusion of {len(results)} items with {pct}% identity convergence.",
            master_markdown=master_md,
        )
