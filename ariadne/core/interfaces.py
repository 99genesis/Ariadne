"""Abstract interfaces (Protocols) for Ariadne OSINT Framework.

Enforces Dependency Inversion Principle (SOLID) by ensuring modules and core services
depend only on protocols, never on concrete implementations.
"""

import argparse
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Protocol, Type, Union, runtime_checkable
from datetime import datetime
from ariadne.core.models import (
    IntelligenceResult,
    NoteEntity,
    ProviderModelInfo,
    TargetEntity,
    SourceType,
    SourceProvenance,
    ReliabilityScore,
    EvidenceItem,
    DimensionContribution,
    ConfidenceExplanation,
    CorrelationReport,
    CircuitBreakerState,
    ProviderHealthMetric,
    ProviderCapabilityManifest,
    PluginCapabilityManifest,
    SocialGraphData,
    RiskProfile,
    NodeType,
    RelationshipType,
    GraphNode,
    GraphEdge,
    GraphSnapshot,
    GraphDiff,
    EventCategory,
    TimelineEvent,
    MasterIntelligenceReport,
)


@runtime_checkable
class ILogger(Protocol):
    """Abstract logger service interface."""

    def debug(self, message: str, **kwargs: Any) -> None:
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        ...

    def error(self, message: str, exc_info: Optional[BaseException] = None, **kwargs: Any) -> None:
        ...

    def critical(self, message: str, exc_info: Optional[BaseException] = None, **kwargs: Any) -> None:
        ...


@runtime_checkable
class ISecretsManager(Protocol):
    """Abstract secrets manager interface for secure credential storage."""

    async def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key from OS secure store or encrypted vault."""
        ...

    async def set_secret(self, key: str, value: str) -> None:
        """Store a secret securely."""
        ...

    async def delete_secret(self, key: str) -> bool:
        """Remove a secret."""
        ...


@runtime_checkable
class ICacheManager(Protocol):
    """Abstract two-tier cache manager interface (Memory + Disk)."""

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Retrieve cached value if valid and not expired."""
        ...

    async def set(self, namespace: str, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store a value in cache with optional TTL."""
        ...

    async def invalidate(self, namespace: str, key: Optional[str] = None) -> None:
        """Clear specific key or entire namespace."""
        ...


@runtime_checkable
class AriadneEventProtocol(Protocol):
    """Protocol for event structures."""

    event_id: str
    timestamp: datetime
    source_plugin: str
    payload: Dict[str, Any]


EventListener = Callable[[Any], Coroutine[Any, Any, None]]


@runtime_checkable
class IEventBus(Protocol):
    """Abstract asynchronous Event Bus interface."""

    def subscribe(self, event_type: Type[Any], listener: EventListener) -> None:
        """Subscribe an async callback to a specific event type."""
        ...

    def unsubscribe(self, event_type: Type[Any], listener: EventListener) -> None:
        """Unsubscribe a previously registered listener."""
        ...

    async def publish(self, event: Any) -> None:
        """Publish an event to all subscribed async listeners concurrently."""
        ...


@runtime_checkable
class IProvider(Protocol):
    """Abstract base provider interface for AI models and OSINT engines."""

    @property
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. google_ai, openai, openrouter)."""
        ...

    @property
    def provider_type(self) -> str:
        """Type of provider: 'ai', 'vision', 'osint_engine', etc."""
        ...

    async def validate_credentials(self, api_key: Optional[str] = None) -> bool:
        """Validate API key or authentication credentials against September 2026 standards."""
        ...

    async def list_models(self) -> List[ProviderModelInfo]:
        """Dynamically fetch available models/engines from the provider API."""
        ...


@runtime_checkable
class IVisionCapable(IProvider, Protocol):
    """Protocol for AI providers capable of image analysis and multi-tier Geo-INT."""

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        model_id: str,
        hint_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze image bytes with optional location hint and return structured JSON predictions."""
        ...


@runtime_checkable
class ITextLLMCapable(IProvider, Protocol):
    """Protocol for AI providers capable of text generation and structuring."""

    async def generate_text(
        self,
        prompt: str,
        model_id: str,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """Generate text or structured JSON response from LLM."""
        ...


@runtime_checkable
class IPlugin(Protocol):
    """Abstract interface for all zero-dependency intelligence plugins."""

    @property
    def plugin_id(self) -> str:
        """Unique plugin ID (e.g. ariadne.builtin.username_intel)."""
        ...

    async def initialize(self, config: Dict[str, Any], event_bus: IEventBus) -> bool:
        """Asynchronously initialize plugin with config and register event listeners."""
        ...

    async def can_handle(self, target: TargetEntity) -> bool:
        """Determine if this plugin can process the given target type or metadata."""
        ...

    async def execute(
        self, target: TargetEntity, providers: Dict[str, IProvider]
    ) -> List[IntelligenceResult]:
        """Execute asynchronous intelligence gathering on the target."""
        ...

    async def cleanup(self) -> None:
        """Release resources on shutdown."""
        ...


@runtime_checkable
class INoteRepository(Protocol):
    """Abstract repository interface for Obsidian Markdown notes and SQLite metadata."""

    async def save_note(self, note: NoteEntity) -> str:
        """Save or update a Markdown note on disk and sync to SQLite index. Returns file path."""
        ...

    async def get_note_by_id(self, note_id: str) -> Optional[NoteEntity]:
        """Retrieve note entity by ID from index or disk."""
        ...

    async def list_notes_by_target(self, vault_name: str, target_id: str) -> List[NoteEntity]:
        """List all notes belonging to a specific target in a vault."""
        ...

    async def delete_note(self, note_id: str) -> bool:
        """Remove note from disk and SQLite index."""
        ...

    async def get_target_summary_stats(self, vault_name: str, target_id: str) -> Dict[str, Any]:
        """High-speed aggregation query returning comprehensive dashboard stats."""
        ...


@runtime_checkable
class IWorkspaceManager(Protocol):
    """Protocol for managing multi-target workspace lifecycle and directory routing."""

    def get_active_target(self) -> Optional[str]:
        ...

    def switch_target(self, target_name: str) -> bool:
        ...

    def create_target(
        self,
        target_name: str,
        description: str = "",
        aliases: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Any:
        ...

    def get_target_paths(self, target_name: Optional[str] = None) -> Any:
        ...

    def list_targets(self) -> List[Dict[str, Any]]:
        ...

    def delete_target(self, target_name: str) -> bool:
        ...

    def ensure_target_workspace(self, target_id: str) -> Any:
        ...


@dataclass
class CommandManualInfo:
    """Detailed manual and help metadata for dynamic CLI guidance and error formatting."""

    name: str
    purpose: str  # Ne işe yarar
    short_usage: str  # Kısa kullanım e.g. username <username>
    usage_pattern: str  # Kullanım e.g. username <username> [seçenekler]
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    workflow: List[str] = field(default_factory=list)  # Ne olur / Sonuç / Yapılan işlemler
    notes: List[str] = field(default_factory=list)
    error_missing_arg: str = ""  # Eksik parametre hata mesajı


@dataclass
class CommandContext:
    """Runtime context passed to command execution."""

    container: Any  # DIContainer reference
    logger: Optional[ILogger] = None
    event_bus: Optional[IEventBus] = None
    vault_name: str = "Ariadne_Workspace"
    vault_root: Any = None
    is_interactive: bool = True
    active_target: Optional[str] = None
    workspace_paths: Optional[Any] = None


@runtime_checkable
class ICommand(Protocol):
    """Protocol for all independent CLI commands."""

    @property
    def command_name(self) -> str:
        """Name of the command triggered from CLI e.g. 'username', 'image'."""
        ...

    @property
    def description(self) -> str:
        """Short description of the command."""
        ...

    @property
    def manual_info(self) -> CommandManualInfo:
        """Detailed manual metadata for dynamic CLI guidance and error formatting."""
        ...

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure command specific CLI arguments and flags."""
        ...

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        """Execute the command asynchronously within the provided context."""
        ...


@runtime_checkable
class IIntelligenceHub(Protocol):
    """Abstract interface for central Intelligence Hub orchestrating tiered execution."""

    async def dispatch_provider(self, provider_id: str, target: TargetEntity, params: Optional[Dict[str, Any]] = None) -> Any:
        """Dispatch request to specific provider with priority, health, and cache checking."""
        ...

    async def execute_multi_provider(self, provider_ids: List[str], target: TargetEntity) -> Dict[str, Any]:
        """Execute multiple providers concurrently under semaphore restrictions."""
        ...


@runtime_checkable
class ISourcePriorityManager(Protocol):
    """Abstract interface for hierarchical source prioritization and early exit evaluation."""

    def get_ordered_tiers(self, providers: List[IProvider]) -> List[List[IProvider]]:
        """Organize providers into tiered execution hierarchy."""
        ...

    def should_early_exit(self, accumulated_results: List[IntelligenceResult]) -> bool:
        """Check if high-confidence results warrant skipping lower tiers."""
        ...


@runtime_checkable
class IProviderCostOptimizer(Protocol):
    """Abstract interface for dynamic provider routing based on cost, quota, and reliability."""

    def select_optimal_provider(self, candidates: List[Any], required_caps: ProviderCapabilityManifest) -> Optional[Any]:
        """Select the best candidate provider matching capabilities and optimization criteria."""
        ...


@runtime_checkable
class IProviderHealthMonitor(Protocol):
    """Abstract interface for tracking provider health metrics and circuit status."""

    def record_success(self, provider_id: str, response_time_ms: float) -> None:
        ...

    def record_failure(self, provider_id: str, error: Exception) -> None:
        ...

    def get_health_score(self, provider_id: str) -> float:
        ...

    def can_execute(self, provider_id: str) -> bool:
        ...


@runtime_checkable
class ICircuitBreaker(Protocol):
    """Abstract interface for circuit breaker state management."""

    def attempt_execution(self) -> bool:
        ...

    def trip() -> None:
        ...

    def reset() -> None:
        ...


@runtime_checkable
class IIncrementalScanEngine(Protocol):
    """Abstract interface for delta intelligence scanning."""

    async def diff_scan_results(self, previous_session_id: str, current_discoveries: List[IntelligenceResult]) -> Dict[str, List[IntelligenceResult]]:
        """Categorize discoveries into NEW, MODIFIED, DELETED, and UNCHANGED."""
        ...


@runtime_checkable
class ICorrelationEngine(Protocol):
    """Abstract interface for multi-dimension reliability-decay-verified correlation engine."""

    async def correlate(self, target: TargetEntity, results: List[IntelligenceResult]) -> CorrelationReport:
        """Run correlation across all 34 dimensions and produce an XAI explanation report."""
        ...


@runtime_checkable
class IRiskEngine(Protocol):
    """Abstract interface for risk assessment and threat exposure computation."""

    async def evaluate_risk(self, target: TargetEntity, correlation: CorrelationReport) -> RiskProfile:
        """Evaluate target threat exposure, breaches, disposable emails, and score risk."""
        ...


@runtime_checkable
class IRiskScoringEngine(Protocol):
    """Abstract interface for synchronous/asynchronous rule-based risk evaluation and scoring."""

    def assess_risk(self, target: TargetEntity, results: List[IntelligenceResult]) -> Any:
        ...


@runtime_checkable
class ITimelineGenerator(Protocol):
    """Abstract interface for chronological event sequence construction and diagram export."""

    def build_timeline(self, target: TargetEntity, results: List[IntelligenceResult]) -> Any:
        ...


@runtime_checkable
class IEntityResolver(Protocol):
    """Abstract interface for canonical entity resolution and fuzzy clustering."""

    def resolve_canonical(self, node_type: NodeType, raw_name: str) -> str:
        ...

    def cluster_entities(self, nodes: List[GraphNode]) -> List[GraphNode]:
        ...


@runtime_checkable
class IGraphRepository(Protocol):
    """Abstract interface for bi-directional property graph repository."""

    async def add_node(self, node: GraphNode) -> str:
        ...

    async def add_edge(self, edge: GraphEdge) -> str:
        ...

    async def get_neighbors(self, node_id: str) -> List[GraphEdge]:
        ...

    async def export_subgraph(self, target_id: str) -> Dict[str, Any]:
        ...


@runtime_checkable
class IGraphVersioningEngine(Protocol):
    """Abstract interface for graph snapshot creation and diffing."""

    async def create_snapshot(self, session_id: str, target_id: str, nodes: Dict[str, GraphNode], edges: Dict[str, GraphEdge]) -> GraphSnapshot:
        ...

    async def compute_diff(self, snapshot_id_before: Optional[str], snapshot_id_after: str) -> GraphDiff:
        ...


@runtime_checkable
class IFusionOrchestrator(Protocol):
    """Abstract interface for end-to-end intelligence fusion pipeline."""

    async def fuse(self, target: TargetEntity, raw_results: List[IntelligenceResult]) -> MasterIntelligenceReport:
        """Synthesize all discoveries into a master intelligence report."""
        ...


@runtime_checkable
class IAuditLogger(Protocol):
    """Abstract interface for enterprise audit logging."""

    async def log_event(self, event_type: str, session_id: str, details: Dict[str, Any]) -> None:
        ...


@runtime_checkable
class IMetricsRegistry(Protocol):
    """Abstract interface for Prometheus/Grafana metrics recording."""

    def record_histogram(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        ...

    def increment_counter(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> None:
        ...

    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        ...

    def export_prometheus_text(self) -> str:
        ...



@runtime_checkable
class ILogger(Protocol):
    """Abstract logger service interface."""

    def debug(self, message: str, **kwargs: Any) -> None:
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        ...

    def error(self, message: str, exc_info: Optional[BaseException] = None, **kwargs: Any) -> None:
        ...

    def critical(self, message: str, exc_info: Optional[BaseException] = None, **kwargs: Any) -> None:
        ...


@runtime_checkable
class ISecretsManager(Protocol):
    """Abstract secrets manager interface for secure credential storage."""

    async def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key from OS secure store or encrypted vault."""
        ...

    async def set_secret(self, key: str, value: str) -> None:
        """Store a secret securely."""
        ...

    async def delete_secret(self, key: str) -> bool:
        """Remove a secret."""
        ...


@runtime_checkable
class ICacheManager(Protocol):
    """Abstract two-tier cache manager interface (Memory + Disk)."""

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Retrieve cached value if valid and not expired."""
        ...

    async def set(self, namespace: str, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store a value in cache with optional TTL."""
        ...

    async def invalidate(self, namespace: str, key: Optional[str] = None) -> None:
        """Clear specific key or entire namespace."""
        ...


@runtime_checkable
class AriadneEventProtocol(Protocol):
    """Protocol for event structures."""

    event_id: str
    timestamp: datetime
    source_plugin: str
    payload: Dict[str, Any]


EventListener = Callable[[Any], Coroutine[Any, Any, None]]


@runtime_checkable
class IEventBus(Protocol):
    """Abstract asynchronous Event Bus interface."""

    def subscribe(self, event_type: Type[Any], listener: EventListener) -> None:
        """Subscribe an async callback to a specific event type."""
        ...

    def unsubscribe(self, event_type: Type[Any], listener: EventListener) -> None:
        """Unsubscribe a previously registered listener."""
        ...

    async def publish(self, event: Any) -> None:
        """Publish an event to all subscribed async listeners concurrently."""
        ...


@runtime_checkable
class IProvider(Protocol):
    """Abstract base provider interface for AI models and OSINT engines."""

    @property
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. google_ai, openai, openrouter)."""
        ...

    @property
    def provider_type(self) -> str:
        """Type of provider: 'ai', 'vision', 'osint_engine', etc."""
        ...

    async def validate_credentials(self, api_key: Optional[str] = None) -> bool:
        """Validate API key or authentication credentials against September 2026 standards."""
        ...

    async def list_models(self) -> List[ProviderModelInfo]:
        """Dynamically fetch available models/engines from the provider API."""
        ...


@runtime_checkable
class IVisionCapable(IProvider, Protocol):
    """Protocol for AI providers capable of image analysis and multi-tier Geo-INT."""

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        model_id: str,
        hint_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze image bytes with optional location hint and return structured JSON predictions."""
        ...


@runtime_checkable
class ITextLLMCapable(IProvider, Protocol):
    """Protocol for AI providers capable of text generation and structuring."""

    async def generate_text(
        self,
        prompt: str,
        model_id: str,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """Generate text or structured JSON response from LLM."""
        ...


@runtime_checkable
class IPlugin(Protocol):
    """Abstract interface for all zero-dependency intelligence plugins."""

    @property
    def plugin_id(self) -> str:
        """Unique plugin ID (e.g. ariadne.builtin.username_intel)."""
        ...

    async def initialize(self, config: Dict[str, Any], event_bus: IEventBus) -> bool:
        """Asynchronously initialize plugin with config and register event listeners."""
        ...

    async def can_handle(self, target: TargetEntity) -> bool:
        """Determine if this plugin can process the given target type or metadata."""
        ...

    async def execute(
        self, target: TargetEntity, providers: Dict[str, IProvider]
    ) -> List[IntelligenceResult]:
        """Execute asynchronous intelligence gathering on the target."""
        ...

    async def cleanup(self) -> None:
        """Release resources on shutdown."""
        ...


@runtime_checkable
class INoteRepository(Protocol):
    """Abstract repository interface for Obsidian Markdown notes and SQLite metadata."""

    async def save_note(self, note: NoteEntity) -> str:
        """Save or update a Markdown note on disk and sync to SQLite index. Returns file path."""
        ...

    async def get_note_by_id(self, note_id: str) -> Optional[NoteEntity]:
        """Retrieve note entity by ID from index or disk."""
        ...

    async def list_notes_by_target(self, vault_name: str, target_id: str) -> List[NoteEntity]:
        """List all notes belonging to a specific target in a vault."""
        ...

    async def delete_note(self, note_id: str) -> bool:
        """Remove note from disk and SQLite index."""
        ...

    async def get_target_summary_stats(self, vault_name: str, target_id: str) -> Dict[str, Any]:
        """High-speed aggregation query returning comprehensive dashboard stats."""
        ...


@runtime_checkable
class IWorkspaceManager(Protocol):
    """Protocol for managing multi-target workspace lifecycle and directory routing."""

    def get_active_target(self) -> Optional[str]:
        ...

    def switch_target(self, target_name: str) -> bool:
        ...

    def create_target(
        self,
        target_name: str,
        description: str = "",
        aliases: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Any:
        ...

    def get_target_paths(self, target_name: Optional[str] = None) -> Any:
        ...

    def list_targets(self) -> List[Dict[str, Any]]:
        ...

    def delete_target(self, target_name: str) -> bool:
        ...

    def ensure_target_workspace(self, target_id: str) -> Any:
        ...


@dataclass
class CommandManualInfo:
    """Detailed manual and help metadata for dynamic CLI guidance and error formatting."""

    name: str
    purpose: str  # Ne işe yarar
    short_usage: str  # Kısa kullanım e.g. username <username>
    usage_pattern: str  # Kullanım e.g. username <username> [seçenekler]
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    workflow: List[str] = field(default_factory=list)  # Ne olur / Sonuç / Yapılan işlemler
    notes: List[str] = field(default_factory=list)
    error_missing_arg: str = ""  # Eksik parametre hata mesajı


@dataclass
class CommandContext:
    """Runtime context passed to command execution."""

    container: Any  # DIContainer reference
    logger: Optional[ILogger] = None
    event_bus: Optional[IEventBus] = None
    vault_name: str = "Ariadne_Workspace"
    vault_root: Any = None
    is_interactive: bool = True
    active_target: Optional[str] = None
    workspace_paths: Optional[Any] = None


@runtime_checkable
class ICommand(Protocol):
    """Protocol for all independent CLI commands."""

    @property
    def command_name(self) -> str:
        """Name of the command triggered from CLI e.g. 'username', 'image'."""
        ...

    @property
    def description(self) -> str:
        """Short description of the command."""
        ...

    @property
    def manual_info(self) -> CommandManualInfo:
        """Detailed manual metadata for dynamic CLI guidance and error formatting."""
        ...

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure command specific CLI arguments and flags."""
        ...

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        """Execute the command asynchronously within the provided context."""
        ...
