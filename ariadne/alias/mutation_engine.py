"""UsernameMutationEngine generating structural and linguistic variations of target usernames."""

import re
from typing import Any, Dict, List, Optional, Set
from ariadne.core.interfaces import ILogger
from ariadne.core.models import TargetEntity, TargetType


class UsernameMutationEngine:
    """Generates structural, linguistic, and numeric permutations of a base username."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        """Initialize mutation engine."""
        self.logger = logger

    def generate_mutations(self, base_name: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Generate deduplicated candidates with mutation type tags and prior confidence."""
        clean = base_name.strip().lower()
        if not clean:
            return []

        candidates: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        def _add(uname: str, mut_type: str, prior: float) -> None:
            if uname and uname not in seen and len(candidates) < max_results:
                seen.add(uname)
                candidates.append({
                    "username": uname,
                    "mutation_type": mut_type,
                    "confidence_prior": prior,
                })

        # 1. Exact match
        _add(clean, "exact", 1.0)

        # Split into tokens if there are separators or camelCase
        tokens = re.split(r"[._\-\s]+", clean)
        if len(tokens) == 1 and len(clean) > 4:
            # Try splitting common first/last name boundaries or halfs
            half = len(clean) // 2
            tokens_split = [clean[:half], clean[half:]]
        else:
            tokens_split = tokens

        # 2. Separators variation
        if len(tokens) > 1:
            _add("_".join(tokens), "separator_underscore", 0.90)
            _add("-".join(tokens), "separator_hyphen", 0.88)
            _add(".".join(tokens), "separator_dot", 0.90)
            _add("".join(tokens), "separator_stripped", 0.92)

        # 3. Common prefixes & suffixes
        suffixes = ["_", "123", "99", "_tr", "_official", "_dev", "hq", "real", "01"]
        prefixes = ["_", "real_", "the_", "i_am_", "its_"]

        for s in suffixes:
            _add(f"{clean}{s}", f"suffix_{s.strip('_')}", 0.75)
        for p in prefixes:
            _add(f"{p}{clean}", f"prefix_{p.strip('_')}", 0.75)

        # 4. Leetspeak / numeric substitution
        leet = (
            clean.replace("o", "0")
            .replace("i", "1")
            .replace("e", "3")
            .replace("a", "4")
            .replace("s", "5")
        )
        if leet != clean:
            _add(leet, "leetspeak", 0.65)

        # 5. Abbreviations if multi-token
        if len(tokens) >= 2 and len(tokens[0]) > 0 and len(tokens[1]) > 0:
            first, last = tokens[0], tokens[1]
            _add(f"{first[0]}{last}", "initial_first_last", 0.80)
            _add(f"{first}_{last[0]}", "first_initial_last", 0.80)
            _add(f"{first[0]}_{last}", "initial_underscore_last", 0.80)

        return candidates

    def expand_target_candidates(self, target: TargetEntity, max_results: int = 30) -> List[TargetEntity]:
        """Produce a list of candidate TargetEntity instances for pre-processing."""
        base = target.display_name if target.target_type == TargetType.USERNAME else target.target_id
        mutations = self.generate_mutations(base, max_results=max_results)

        entities: List[TargetEntity] = []
        for mut in mutations:
            uname = mut["username"]
            meta = dict(target.metadata)
            meta.update({
                "mutation_type": mut["mutation_type"],
                "confidence_prior": mut["confidence_prior"],
                "base_target_id": target.target_id,
            })
            entities.append(
                TargetEntity(
                    target_id=f"{target.target_id}_{uname}" if uname != base else target.target_id,
                    target_type=TargetType.USERNAME,
                    display_name=uname,
                    metadata=meta,
                )
            )
        return entities
