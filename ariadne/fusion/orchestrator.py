"""IntelligenceFusionOrchestrator orchestrating end-to-end multi-layer intelligence synthesis."""

from typing import Any, Dict, List, Optional
from ariadne.core.interfaces import (
    ICorrelationEngine,
    IFusionOrchestrator,
    ILogger,
    IRiskScoringEngine,
    ITimelineGenerator,
)
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.correlation.engine import CorrelationEngine
from ariadne.graph.repository import GraphRepository
from ariadne.graph.resolver import EntityResolver
from ariadne.graph.versioning import GraphVersioningEngine
from ariadne.risk.engine import RiskScoringEngine
from ariadne.timeline.generator import TimelineGenerator
from ariadne.fusion.models import MasterIntelligenceReport
from ariadne.fusion.report_builder import MasterReportBuilder


class IntelligenceFusionOrchestrator(IFusionOrchestrator):
    """Central orchestrator directing the intelligence pipeline: correlation, graph, risk, timeline, and master report."""

    def __init__(
        self,
        correlation_engine: Optional[ICorrelationEngine] = None,
        graph_repository: Optional[GraphRepository] = None,
        risk_engine: Optional[IRiskScoringEngine] = None,
        timeline_generator: Optional[ITimelineGenerator] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        self.logger = logger
        self.correlation_engine = correlation_engine or CorrelationEngine(logger=logger)
        self.graph_repository = graph_repository or GraphRepository()
        self.risk_engine = risk_engine or RiskScoringEngine(logger=logger)
        self.timeline_generator = timeline_generator or TimelineGenerator(logger=logger)

    async def fuse(
        self,
        target: TargetEntity,
        raw_results: List[IntelligenceResult],
    ) -> MasterIntelligenceReport:
        """Synthesize discoveries across all layers and build the Master Intelligence Report."""
        if self.logger:
            self.logger.info(f"Starting Intelligence Fusion for target {target.target_id} across {len(raw_results)} items.")

        # 1. Correlation, Provenance, Time Decay, Verification & XAI
        if hasattr(self.correlation_engine, "correlate_findings"):
            fusion_score, correlation_details = self.correlation_engine.correlate_findings(target, raw_results)
            # If the correlation engine processed/verified the results, retrieve updated list
            verified_results = self.correlation_engine.apply_provenance_and_decay(raw_results) if hasattr(self.correlation_engine, "apply_provenance_and_decay") else raw_results
        else:
            fusion_score = 0.5
            correlation_details = {"overall_score": 0.5}
            verified_results = raw_results

        # 2. Entity Resolution & Versioned Graph Snapshot
        nodes, edges = EntityResolver.resolve_from_results(target.target_id, target.display_name, verified_results)
        history = self.graph_repository.get_snapshot_history(target.target_id)
        next_version = len(history) + 1
        snapshot = GraphVersioningEngine.create_snapshot(target.target_id, next_version, nodes, edges)
        self.graph_repository.store_snapshot(snapshot)

        # 3. Risk Assessment
        risk_assessment = self.risk_engine.assess_risk(target, verified_results) if hasattr(self.risk_engine, "assess_risk") else None

        # 4. Timeline Generation
        timeline = self.timeline_generator.build_timeline(target, verified_results) if hasattr(self.timeline_generator, "build_timeline") else None

        # 5. Master Report Building
        report = MasterReportBuilder.build_master_report(
            target=target,
            results=verified_results,
            fusion_score=fusion_score,
            correlation_details=correlation_details,
            risk_assessment=risk_assessment,
            timeline=timeline,
            graph_snapshot=snapshot,
        )

        if self.logger:
            self.logger.info(f"Intelligence Fusion complete for {target.target_id}. Score: {fusion_score:.2f}")

        return report
