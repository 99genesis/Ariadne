"""TimelineGenerator implementing ITimelineGenerator for chronological event construction and Mermaid export."""

from datetime import datetime, timezone
from typing import List, Optional
from ariadne.core.interfaces import ITimelineGenerator, ILogger
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.timeline.models import TargetTimeline, TimelineEvent


class TimelineGenerator(ITimelineGenerator):
    """Constructs chronological event timelines across all intelligence discoveries and formats reports."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        self.logger = logger

    def build_timeline(self, target: TargetEntity, results: List[IntelligenceResult]) -> TargetTimeline:
        """Analyze intelligence results, extract timestamps, and compile chronological event sequence."""
        events: List[TimelineEvent] = []

        # Target creation baseline event
        if target.created_at:
            events.append(
                TimelineEvent(
                    event_id=f"evt:target:created:{target.target_id}",
                    timestamp=target.created_at.replace(tzinfo=timezone.utc) if target.created_at.tzinfo is None else target.created_at,
                    event_type="creation",
                    title=f"Target Vault Created: {target.display_name}",
                    description="Ariadne investigation vault initialized.",
                    source_id="workspace_manager",
                    confidence=1.0,
                    tags=["#timeline/creation"],
                )
            )

        for i, r in enumerate(results):
            meta = r.metadata or {}
            ts = r.discovered_at or datetime.now(timezone.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            # Check if metadata provides explicit creation date (e.g., account registered 2018-05-12)
            created_str = meta.get("created_at") or meta.get("creation_date")
            if created_str:
                try:
                    if isinstance(created_str, datetime):
                        c_ts = created_str.replace(tzinfo=timezone.utc) if created_str.tzinfo is None else created_str
                    else:
                        c_ts = datetime.fromisoformat(str(created_str).replace("Z", "+00:00"))
                    events.append(
                        TimelineEvent(
                            event_id=f"evt:creation:{r.source_plugin or 'plugin'}:{i}",
                            timestamp=c_ts,
                            event_type="creation",
                            title=f"Account Created: {r.title}",
                            description=f"Platform {meta.get('platform', r.source_plugin)} account registered.",
                            source_id=getattr(r, "url", "") or r.source_plugin or "unknown",
                            confidence=0.9,
                            tags=["#timeline/account_creation"],
                        )
                    )
                except Exception:
                    pass

            # Discovery event
            events.append(
                TimelineEvent(
                    event_id=f"evt:discovery:{r.source_plugin or 'plugin'}:{i}",
                    timestamp=ts,
                    event_type="discovery",
                    title=f"Discovery: {r.title}",
                    description=r.content_markdown[:150] if r.content_markdown else "Intelligence finding recorded.",
                    source_id=getattr(r, "url", "") or r.source_plugin or "unknown",
                    confidence=r.confidence_score,
                    tags=["#timeline/discovery"] + r.tags,
                )
            )

        events.sort(key=lambda e: e.timestamp)
        earliest = events[0].timestamp if events else None
        latest = events[-1].timestamp if events else None

        return TargetTimeline(
            target_id=target.target_id,
            events=events,
            generated_at=datetime.now(timezone.utc),
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

    def to_markdown(self, timeline: TargetTimeline) -> str:
        """Format timeline into a clean markdown document with Mermaid sequence/Gantt chart."""
        lines = [
            f"### 🕒 Investigation Timeline (`{timeline.target_id}`)",
            f"**Total Events:** `{len(timeline.events)}`",
            "",
            "#### Chronological Event Log Table",
            "| Timestamp (UTC) | Event Type | Title | Confidence | Source |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for e in timeline.events:
            ts_str = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"| `{ts_str}` | `{e.event_type}` | **{e.title}** | `{e.confidence:.2f}` | `{e.source_id}` |")

        lines.append("")
        lines.append("#### Mermaid Timeline Chart")
        lines.append("```mermaid")
        lines.append("timeline")
        lines.append(f"    title Target Timeline - {timeline.target_id}")

        # Group by date for Mermaid timeline syntax
        grouped = {}
        for e in timeline.events:
            date_key = e.timestamp.strftime("%Y-%m-%d")
            grouped.setdefault(date_key, []).append(e.title.replace(":", " -"))

        for dt, ev_list in grouped.items():
            ev_str = " : ".join(ev_list[:3])
            lines.append(f"    {dt} : {ev_str}")
        lines.append("```")

        return "\n".join(lines)
