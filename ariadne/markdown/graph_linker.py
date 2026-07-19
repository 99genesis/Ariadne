"""Graph Linker for injecting and normalizing Obsidian [[Double Bracket]] links."""

import re
from typing import List, Set


class GraphLinker:
    """Scans markdown text and normalizes double bracket links around known entities."""

    LINK_REGEX = re.compile(r"\[\[(.*?)\]\]")

    @classmethod
    def normalize_link(cls, entity_name: str) -> str:
        """Ensure entity name is cleanly wrapped in double brackets without illegal characters."""
        clean = entity_name.strip().replace("[[", "").replace("]]", "")
        clean = clean.replace("#", "_").replace(":", "_").replace("/", "_").replace("\\", "_")
        return f"[[{clean}]]"

    @classmethod
    def extract_links(cls, content: str) -> List[str]:
        """Extract all unique double bracket link targets from a markdown string."""
        matches = cls.LINK_REGEX.findall(content)
        return sorted(list(set(matches)))

    @classmethod
    def inject_links(cls, text: str, entity_keywords: List[str]) -> str:
        """Wrap known keyword strings in text with double bracket links if not already linked."""
        result = text
        for kw in entity_keywords:
            if not kw or len(kw) < 3:
                continue
            # Regex to wrap keyword only if not already inside [[ ]]
            pattern = re.compile(rf"(?<!\[\[)\b({re.escape(kw)})\b(?!\]\])", re.IGNORECASE)
            result = pattern.sub(r"[[\1]]", result)
        return result
