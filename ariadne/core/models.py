"""Domain data models for Ariadne OSINT Framework.

All entities exchanged between plugins, providers, event bus, and markdown layer
are strictly typed using Pydantic BaseModel and Python dataclasses.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Hierarchical source type classifications for priority and trust scoring."""

    OFFICIAL_API = "Official API"
    OFFICIAL_WEBSITE = "Official Website"
    VERIFIED_PROFILE = "Verified Profile"
    PUBLIC_SOURCE = "Public Source"
    SEARCH_ENGINE = "Search Engine"
    ARCHIVE = "Archive"
    THIRD_PARTY = "Third Party"
    CACHED_RESULT = "Cached Result"
    AI_INFERENCE = "AI Inference"


class VerificationLevel(str, Enum):
    """Level of verification supporting an evidence discovery."""

    VERIFIED_BY_CRYPTO = "Verified by Crypto/PGP"
    VERIFIED_BY_PLATFORM = "Verified by Platform (Official Badge)"
    DIRECT_CROSS_LINK = "Direct Cross-Link in Bio/Website"
    CLAIMED = "Claimed/Self-Reported"
    INFERRED = "Inferred via Statistical Correlation"
    UNVERIFIED = "Unverified/Anecdotal"


class SourceProvenance(BaseModel):
    """Full unbroken chain of custody and provenance trace for every discovered item."""

    provider_id: str = Field(..., description="Provider ID that produced the data")
    api_name: str = Field(..., description="API or engine name")
    url: str = Field(..., description="Origin URL or endpoint")
    endpoint: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str = Field(..., description="SHA-256 hash of the raw response payload")
    verification_level: VerificationLevel = Field(default=VerificationLevel.UNVERIFIED)
    reliability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_contribution: float = Field(default=0.0, ge=0.0, le=1.0)
    scan_session_id: str = Field(default="", description="UUID representing the current execution scan")
    parent_provenance_id: Optional[str] = Field(default=None, description="Cryptographic hash of parent discovery")
    immutable_hash: str = Field(default="", description="Immutable SHA-256 chain-of-custody hash")


class TargetType(str, Enum):
    """Supported target entities in Ariadne."""

    PERSON = "person"
    ORGANIZATION = "organization"
    USERNAME = "username"
    EMAIL = "email"
    PHONE = "phone"
    DOMAIN = "domain"
    IP = "ip"
    IMAGE = "image"
    HASH = "hash"
    CUSTOM = "custom"


class TargetEntity(BaseModel):
    """Represents the primary target under investigation within a vault."""

    target_id: str = Field(..., description="Unique identifier or name of the target (e.g. Hedef_Ahmet)")
    target_type: TargetType = Field(default=TargetType.PERSON, description="Category of the target entity")
    display_name: str = Field(..., description="Human-readable title")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supplemental data (e.g., {'email': 'test@example.com', 'hint_location': 'İstanbul'})",
    )


class IntelligenceResult(BaseModel):
    """Represents an atomic discovery produced by an intelligence plugin."""

    title: str = Field(..., description="Title of the finding note")
    entity_type: str = Field(..., description="Type of intelligence (social_profile, location, phone, ip, etc.)")
    source_plugin: str = Field(..., description="Plugin ID that discovered this finding")
    provider_used: Optional[str] = Field(default=None, description="Provider ID if an AI or external API was used")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level between 0.0 and 1.0")
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = Field(default_factory=list, description="Tags for Obsidian (#osint/social, #status/verified)")
    links_to: List[str] = Field(
        default_factory=list,
        description="List of Obsidian double-bracket links (e.g., ['[[Hedef_Ahmet]]', '[[İstanbul_Location]]'])",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured key-value pairs representing technical details to be placed in YAML frontmatter",
    )
    content_markdown: str = Field(
        default="",
        description="Optional markdown body content detailing the finding below the YAML frontmatter",
    )
    provenance: Optional[SourceProvenance] = Field(
        default=None,
        description="Unbroken chain of custody and origin trace for this discovery",
    )


class NoteEntity(BaseModel):
    """Represents a physical Markdown note file stored inside an Obsidian vault."""

    note_id: str = Field(..., description="YAML frontmatter unique ID")
    vault_name: str = Field(..., description="Name of the parent vault folder")
    relative_path: str = Field(..., description="Relative path within the vault (e.g. Sosyal_Medya/Ahmet_Twitter.md)")
    title: str = Field(..., description="Note title")
    target_id: str = Field(..., description="Primary target ID associated with this note")
    entity_type: str = Field(..., description="Type of entity")
    source_module: str = Field(..., description="Plugin ID that generated this note")
    provider_used: Optional[str] = Field(default=None)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list, description="All double-bracket links present in the note")
    raw_frontmatter: Dict[str, Any] = Field(default_factory=dict)
    body_content: str = Field(default="")


class ProviderModelInfo(BaseModel):
    """Describes a specific model or engine offered by a dynamic provider."""

    model_id: str = Field(..., description="Unique model identifier (e.g., gemini-1.5-pro-latest)")
    display_name: str = Field(..., description="Human-readable name shown in CLI selection")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities: ['text', 'vision', 'json_mode']")
    context_window: int = Field(default=128000, description="Max token context window")
    is_free_tier_compatible: bool = Field(default=True, description="Whether the model works under standard quotas")


class ReliabilityScore(BaseModel):
    """Detailed reliability metrics for an individual evidence item."""

    source_type: SourceType = Field(...)
    verification_level: VerificationLevel = Field(...)
    source_trust_level: float = Field(..., ge=0.0, le=1.0, description="Trust coefficient [0.0 - 1.0]")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Final reliability index [0.0 - 1.0]")
    trust_rationale: str = Field(..., description="Explanation of why this source is trusted or distrusted")


class EvidenceItem(BaseModel):
    """Represents a specific piece of evidence supporting a correlation or graph relationship."""

    evidence_id: str = Field(..., description="Unique evidence ID")
    dimension: str = Field(..., description="Scoring dimension (e.g., 'avatar_similarity', 'exif_gps')")
    description: str = Field(..., description="Human-readable explanation of the match")
    confidence_contribution: float = Field(..., ge=0.0, le=1.0, description="Score contribution [0.0 - 1.0]")
    source_plugin: str = Field(..., description="Plugin or provider that discovered this evidence")
    reliability: ReliabilityScore = Field(..., description="Reliability evaluation of the discovery source")
    provenance: Optional[SourceProvenance] = Field(default=None, description="Unbroken chain of custody and origin")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class DimensionContribution(BaseModel):
    """Detailed XAI breakdown of a single dimension's contribution to the identity score."""

    dimension_name: str = Field(...)
    raw_quality_score: float = Field(..., ge=0.0, le=1.0)
    dimension_weight: float = Field(..., ge=0.0, le=1.0)
    reliability_coefficient: float = Field(..., ge=0.0, le=1.0)
    decay_coefficient: float = Field(default=1.0, ge=0.0, le=1.0, description="Time-based decay D(t)")
    corroboration_multiplier: float = Field(default=1.0, description="Multi-source verification boost M_v")
    final_contribution_score: float = Field(..., description="Net contribution added to the total score e.g. +0.18")
    explanation_text: str = Field(..., description="Human-readable rationale for this contribution")


class ConfidenceExplanation(BaseModel):
    """Explainable AI (XAI) breakdown of positive factors, missing indicators, and exact contributions."""

    summary_text: str = Field(...)
    positive_reasons: List[str] = Field(default_factory=list, description="List e.g. ['✓ Username Exact Match']")
    negative_reasons: List[str] = Field(default_factory=list, description="List e.g. ['✗ Email Unknown']")
    dimension_contributions: List[DimensionContribution] = Field(default_factory=list, description="Complete 34-dimension table")
    key_decisive_factors: List[str] = Field(default_factory=list)


class CorrelationReport(BaseModel):
    """Aggregated identity correlation results across all 34+ dimensions with XAI and provenance."""

    target_id: str = Field(...)
    identity_score: float = Field(..., ge=0.0, le=1.0, description="Overall probability that findings belong to one entity")
    confidence_level: str = Field(..., description="HIGH, MEDIUM, LOW, or UNVERIFIED")
    explanation: ConfidenceExplanation = Field(..., description="Human-readable XAI breakdown & contribution table")
    dimension_scores: Dict[str, float] = Field(default_factory=dict, description="Breakdown per dimension")
    evidence_list: List[EvidenceItem] = Field(default_factory=list)
    known_aliases: List[str] = Field(default_factory=list)
    possible_real_name: Optional[str] = Field(default=None)
    possible_country: Optional[str] = Field(default=None)
    possible_city: Optional[str] = Field(default=None)
    possible_languages: List[str] = Field(default_factory=list)
    possible_occupation: Optional[str] = Field(default=None)


class CircuitBreakerState(str, Enum):
    """Operational state of a provider's circuit breaker."""

    CLOSED = "CLOSED"  # Normal operation; requests pass through
    OPEN = "OPEN"  # Tripped due to failures; fails fast immediately
    HALF_OPEN = "HALF_OPEN"  # Testing recovery with single probe request


class ProviderHealthMetric(BaseModel):
    """Health, performance, and circuit breaker telemetry for an individual provider."""

    provider_id: str = Field(...)
    health_score: float = Field(default=100.0, ge=0.0, le=100.0)
    availability_percentage: float = Field(default=100.0, ge=0.0, le=100.0)
    avg_response_time_ms: float = Field(default=0.0)
    success_rate: float = Field(default=100.0, ge=0.0, le=100.0)
    failure_count: int = Field(default=0)
    timeout_count: int = Field(default=0)
    last_successful_request: Optional[datetime] = Field(default=None)
    last_failure: Optional[datetime] = Field(default=None)
    rate_limit_status: str = Field(default="OK")
    circuit_state: CircuitBreakerState = Field(default=CircuitBreakerState.CLOSED)


class ProviderCapabilityManifest(BaseModel):
    """Published capabilities of a dynamic provider for automated discovery and routing."""

    provider_id: str = Field(...)
    display_name: str = Field(...)
    supports_ai: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    supports_ocr: bool = Field(default=False)
    supports_graph: bool = Field(default=True)
    supports_timeline: bool = Field(default=True)
    supports_archive: bool = Field(default=False)
    supports_social_graph: bool = Field(default=False)
    supports_reverse_image: bool = Field(default=False)
    supports_geolocation: bool = Field(default=False)
    supports_cache: bool = Field(default=True)
    supports_delta_scan: bool = Field(default=True)
    supports_bulk_lookup: bool = Field(default=False)
    cost_per_query_units: float = Field(default=1.0)


class PluginCapabilityManifest(BaseModel):
    """Published capabilities of an intelligence plugin for dynamic pipeline inspection."""

    plugin_id: str = Field(...)
    display_name: str = Field(...)
    supported_target_types: List[str] = Field(default_factory=list)
    produced_evidence_types: List[str] = Field(default_factory=list)
    supported_providers: List[str] = Field(default_factory=list)
    supported_intelligence_categories: List[str] = Field(default_factory=list)
    supports_ai: bool = Field(default=False)
    supports_ocr: bool = Field(default=False)
    supports_image_analysis: bool = Field(default=False)
    supports_timeline: bool = Field(default=True)
    supports_graph: bool = Field(default=True)


class SocialGraphData(BaseModel):
    """Normalized social relationship structures harvested by SocialGraphCollector without scraping enforcement."""

    platform: str = Field(...)
    profile_username: str = Field(...)
    is_data_available: bool = Field(default=True)
    status_message: str = Field(default="Success", description="e.g. 'Platform tarafından sağlanmıyor' or 'Gizli profil'")
    following: List[str] = Field(default_factory=list)
    followers: List[str] = Field(default_factory=list)
    mutual_followers: List[str] = Field(default_factory=list)
    mutual_following: List[str] = Field(default_factory=list)
    friends: List[str] = Field(default_factory=list)
    connections: List[str] = Field(default_factory=list)
    public_lists: List[str] = Field(default_factory=list)
    public_mentions: List[str] = Field(default_factory=list)
    public_communities: List[str] = Field(default_factory=list)
    public_organizations: List[str] = Field(default_factory=list)


class RiskProfile(BaseModel):
    """Evaluates target exposure, security posture, and technical threat indicators."""

    target_id: str = Field(...)
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Overall risk index [0.0 - 100.0]")
    risk_level: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW, or SAFE")
    known_breaches: List[str] = Field(default_factory=list, description="Names of data breaches involving target")
    leaked_credentials_count: int = Field(default=0)
    disposable_email_detected: bool = Field(default=False)
    suspicious_domains: List[str] = Field(default_factory=list)
    public_exposure_rating: str = Field(default="MODERATE")
    risk_factors_breakdown: Dict[str, float] = Field(default_factory=dict)
    recommended_next_steps: List[str] = Field(default_factory=list)


class NodeType(str, Enum):
    """Supported canonical entity node types in graph repository."""

    PERSON = "Person"
    USERNAME = "Username"
    EMAIL = "Email"
    PHONE = "Phone"
    IMAGE = "Image"
    WEBSITE = "Website"
    DOMAIN = "Domain"
    COMPANY = "Company"
    ORGANIZATION = "Organization"
    ADDRESS = "Address"
    COORDINATE = "Coordinate"
    VEHICLE = "Vehicle"
    DOCUMENT = "Document"
    WALLET = "Wallet"
    IP = "IP"
    ASN = "ASN"
    COUNTRY = "Country"
    CITY = "City"
    PROVIDER = "Provider"
    EVENT = "Event"
    SOCIAL_ACCOUNT = "Social_Account"
    GAMING_ACCOUNT = "Gaming_Account"
    FORUM_ACCOUNT = "Forum_Account"


class RelationshipType(str, Enum):
    """Supported directed relationship types in graph repository."""

    OWNS = "owns"
    USES = "uses"
    REGISTERED_TO = "registered_to"
    VISITED = "visited"
    MENTIONED = "mentioned"
    CREATED = "created"
    LINKED_TO = "linked_to"
    BELONGS_TO = "belongs_to"
    FRIEND_OF = "friend_of"
    FOLLOWS = "follows"
    MEMBER_OF = "member_of"
    WORKS_AT = "works_at"
    LOCATED_IN = "located_in"
    SHARES_EMAIL = "shares_email"
    SHARES_PHONE = "shares_phone"
    SHARES_AVATAR = "shares_avatar"
    SHARES_DOMAIN = "shares_domain"
    SHARES_IMAGE = "shares_image"
    SAME_PERSON = "same_person"
    POSSIBLE_MATCH = "possible_match"
    APPEARED_WITH = "appeared_with"
    CREATED_EVENT = "created_event"


class GraphNode(BaseModel):
    """Represents a discrete entity node inside the Obsidian/SQLite graph."""

    node_id: str = Field(..., description="Canonical ID e.g. Person_scarface or Company_OpenAI")
    node_type: NodeType = Field(...)
    label: str = Field(..., description="Display label")
    obsidian_link: str = Field(..., description="Double bracket representation e.g. [[Company_OpenAI]]")
    raw_aliases: List[str] = Field(default_factory=list, description="Merged raw strings e.g. ['OpenAI Inc.', 'Open AI']")
    properties: Dict[str, Any] = Field(default_factory=dict)
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphEdge(BaseModel):
    """Represents a directed, weighted relationship edge between two canonical nodes."""

    edge_id: str = Field(..., description="Unique edge UUID")
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")
    relationship: RelationshipType = Field(...)
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship strength/thickness coefficient [0.0 - 1.0]")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Verified confidence of the edge")
    evidence_count: int = Field(default=1, description="Number of distinct evidence items supporting this edge")
    evidence_sources: List[str] = Field(default_factory=list, description="List of provider IDs supporting this connection")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphSnapshot(BaseModel):
    """Immutable point-in-time snapshot of the entire target knowledge graph."""

    snapshot_id: str = Field(..., description="Unique snapshot UUID")
    scan_session_id: str = Field(..., description="Scan session ID that generated this snapshot")
    target_id: str = Field(...)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    nodes: Dict[str, GraphNode] = Field(default_factory=dict)
    edges: Dict[str, GraphEdge] = Field(default_factory=dict)
    node_count: int = Field(default=0)
    edge_count: int = Field(default=0)


class GraphDiff(BaseModel):
    """Diff analysis report comparing two graph snapshots across time (`Graph History`)."""

    snapshot_id_before: Optional[str] = Field(default=None)
    snapshot_id_after: str = Field(...)
    added_nodes: List[GraphNode] = Field(default_factory=list)
    deleted_nodes: List[GraphNode] = Field(default_factory=list)
    modified_nodes: List[GraphNode] = Field(default_factory=list)
    added_edges: List[GraphEdge] = Field(default_factory=list)
    deleted_edges: List[GraphEdge] = Field(default_factory=list)
    modified_edges: List[GraphEdge] = Field(default_factory=list)


class EventCategory(str, Enum):
    """Categories of timeline events."""

    ACCOUNT_CREATION = "Account Creation"
    DOMAIN_REGISTRATION = "Domain Registration"
    LOCATION_SIGHTING = "Location Sighting"
    PROFILE_UPDATE = "Profile Update"
    BREACH_OCCURRENCE = "Breach Occurrence"
    CRYPTO_TRANSACTION = "Crypto Transaction"
    GENERAL = "General Event"


class TimelineEvent(BaseModel):
    """Represents a chronological intelligence discovery event."""

    event_id: str = Field(...)
    timestamp: datetime = Field(...)
    category: EventCategory = Field(default=EventCategory.GENERAL)
    title: str = Field(...)
    description: str = Field(...)
    source_plugin: str = Field(...)
    provenance: Optional[SourceProvenance] = Field(default=None)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    links: List[str] = Field(default_factory=list)


class MasterIntelligenceReport(BaseModel):
    """Synthesized Master Intelligence Report combining all correlation, risk, graph, and timeline analysis."""

    report_id: str = Field(...)
    target_id: str = Field(...)
    target_type: str = Field(...)
    title: str = Field(...)
    identity_score: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str = Field(...)
    risk_profile: RiskProfile = Field(...)
    correlation_report: CorrelationReport = Field(...)
    graph_snapshot_id: Optional[str] = Field(default=None)
    timeline_events: List[TimelineEvent] = Field(default_factory=list)
    known_aliases: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scan_session_id: str = Field(default="")
    tags: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)

