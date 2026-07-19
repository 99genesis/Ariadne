"""EntityCanonicalizer normalizing and standardizing raw entities into canonical keys."""

import re


class EntityCanonicalizer:
    """Normalizes target discoveries across disparate platform representations into canonical identifiers."""

    @staticmethod
    def canonicalize(entity_type: str, raw_value: str, platform: str = "") -> str:
        """Compute standardized canonical identifier for deduplication and graph resolution."""
        etype = (entity_type or "unknown").strip().lower()
        val = (raw_value or "").strip().lower()
        plat = (platform or "").strip().lower()

        # Clean URL prefixes if value is URL
        val = re.sub(r"^https?://(www\.)?", "", val).rstrip("/")

        if etype in ("username", "social_profile", "social"):
            if plat:
                return f"username:{plat}:{val.split('/')[-1]}"
            return f"username:{val}"
        elif etype == "email":
            return f"email:{val}"
        elif etype == "phone":
            digits = re.sub(r"\D", "", val)
            return f"phone:{digits}"
        elif etype in ("domain", "website", "url"):
            domain = val.split("/")[0]
            return f"domain:{domain}"
        elif etype == "ip":
            return f"ip:{val}"
        else:
            clean_str = re.sub(r"[^a-z0-9_.-]", "_", val)
            return f"{etype}:{clean_str}"
