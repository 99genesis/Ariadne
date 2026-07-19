"""Internationalization (i18n) translation engine for Ariadne CLI.

Supports seamless language switching across en, ru, zh, and tr with missing-key
fallback to English.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class I18nManager:
    """Manages loading dictionaries and resolving translation keys."""

    def __init__(self, locales_dir: Optional[Path] = None, current_lang: str = "en") -> None:
        self.locales_dir = Path(locales_dir) if locales_dir is not None else Path(__file__).parent / "locales"
        self.current_lang = current_lang.lower()
        self._dictionaries: Dict[str, Dict[str, Any]] = {}
        self._load_locales()

    def _load_locales(self) -> None:
        if not self.locales_dir.exists():
            return

        for lang_file in self.locales_dir.glob("*.json"):
            lang_code = lang_file.stem.lower()
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    self._dictionaries[lang_code] = json.load(f)
            except Exception:
                pass

    def set_language(self, lang_code: str) -> None:
        """Switch current active language."""
        if lang_code.lower() in self._dictionaries or lang_code.lower() in ("en", "ru", "zh", "tr"):
            self.current_lang = lang_code.lower()

    def get(self, key: str, **kwargs: Any) -> str:
        """Retrieve translation string by dot-separated key with formatting interpolation."""
        # Check current language
        lang_dict = self._dictionaries.get(self.current_lang, {})
        val = self._resolve_nested(lang_dict, key)

        # Fallback to en if missing
        if val is None and self.current_lang != "en":
            en_dict = self._dictionaries.get("en", {})
            val = self._resolve_nested(en_dict, key)

        if val is None:
            return key

        if kwargs:
            try:
                return str(val).format(**kwargs)
            except Exception:
                return str(val)
        return str(val)

    def _resolve_nested(self, dictionary: Dict[str, Any], key: str) -> Optional[Any]:
        parts = key.split(".")
        current: Any = dictionary
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
