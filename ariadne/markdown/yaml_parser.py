"""YAML Frontmatter parser and builder.

Strictly handles separating YAML frontmatter from markdown body and serializing
metadata dictionaries into valid, clean YAML blocks without file I/O side effects.
"""

import re
from typing import Any, Dict, Tuple
import yaml


class YamlParser:
    """Parses and serializes YAML frontmatter blocks."""

    FRONTMATTER_REGEX = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)$", re.DOTALL)

    @classmethod
    def parse(cls, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter dictionary and markdown body from file string.

        Args:
            content: Raw string read from a markdown note.

        Returns:
            Tuple containing (frontmatter_dict, body_content_string).
        """
        if not content.strip():
            return {}, ""

        match = cls.FRONTMATTER_REGEX.match(content)
        if not match:
            return {}, content.strip()

        yaml_text, body_text = match.groups()
        try:
            metadata: Dict[str, Any] = yaml.safe_load(yaml_text) or {}
            return metadata, body_text.strip()
        except Exception:
            # If YAML parsing fails, return empty dict and preserve body
            return {}, content.strip()

    @classmethod
    def dump(cls, frontmatter: Dict[str, Any], body: str) -> str:
        """Serialize frontmatter dictionary and body into standard markdown note format.

        Args:
            frontmatter: Dictionary of metadata to format inside --- block.
            body: Markdown body text.

        Returns:
            Complete markdown string with YAML frontmatter.
        """
        if not frontmatter:
            return body.strip()

        yaml_str = yaml.dump(
            frontmatter,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ).strip()

        return f"---\n{yaml_str}\n---\n\n{body.strip()}\n"
