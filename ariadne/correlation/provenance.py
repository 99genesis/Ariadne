"""ProvenanceChainBuilder for creating immutable SHA-256 chain-of-custody hashes on intelligence items."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from ariadne.core.models import SourceProvenance, VerificationLevel


class ProvenanceChainBuilder:
    """Builds cryptographic chain-of-custody provenance records for intelligence discoveries."""

    @staticmethod
    def compute_hash(payload: Dict[str, Any], origin_module: str, parent_hash: Optional[str] = None) -> str:
        """Compute SHA-256 immutable hash of discovery payload + parent hash."""
        raw = f"{origin_module}:{parent_hash or 'root'}:{json.dumps(payload, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def build_provenance(
        cls,
        source_id: str,
        origin_module: str,
        confidence: float,
        payload: Dict[str, Any],
        parent_provenance: Optional[SourceProvenance] = None,
        verification_level: VerificationLevel = VerificationLevel.UNVERIFIED,
    ) -> SourceProvenance:
        """Construct a validated SourceProvenance instance with cryptographic hash."""
        parent_id = parent_provenance.immutable_hash if parent_provenance and parent_provenance.immutable_hash else None
        imm_hash = cls.compute_hash(payload, origin_module, parent_id)
        url_val = payload.get("url") or f"https://{origin_module}/{source_id}"
        return SourceProvenance(
            provider_id=origin_module,
            api_name=origin_module,
            url=url_val,
            timestamp=datetime.now(timezone.utc),
            content_hash=imm_hash,
            verification_level=verification_level,
            reliability_score=confidence,
            confidence_contribution=confidence,
            parent_provenance_id=parent_id,
            immutable_hash=imm_hash,
        )
