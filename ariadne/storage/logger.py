"""Centralized rotating logger with sensitive data masking and Rich console output."""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional
from rich.console import Console
from rich.logging import RichHandler

from ariadne.core.interfaces import ILogger


class AriadneLogger(ILogger):
    """Technical rotating logger supporting file backups and sensitive credential scrubbing."""

    SENSITIVE_PATTERNS = [
        # Mask API keys (AI Studio, OpenAI, etc.)
        (re.compile(r'(?i)(api[_-]?key[\s:=]+)([A-Za-z0-9_-]{16,})'), r'\1***MASKED_KEY***'),
        # Mask Bearer tokens
        (re.compile(r'(?i)(bearer[\s]+)([A-Za-z0-9._-]{20,})'), r'\1***MASKED_TOKEN***'),
        # Mask passwords
        (re.compile(r'(?i)(password|passwd|pwd)([\s:=]+)([^\s,]{4,})'), r'\1\2***MASKED_PWD***'),
    ]

    def __init__(
        self,
        name: str = "Ariadne",
        log_dir: Optional[Path] = None,
        level: str = "INFO",
        console_output: bool = True,
        max_mb: int = 20,
        backup_count: int = 5,
        mask_sensitive: bool = True,
    ) -> None:
        """Initialize logger with file and console handlers."""
        self.mask_sensitive = mask_sensitive
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.logger.handlers.clear()

        # Formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s | [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # File Rotating Handler
        if log_dir is None:
            log_dir = Path("Ariadne_Workspace") / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "ariadne.log"

        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Rich Console Handler
        if console_output:
            console = Console(stderr=True)
            rich_handler = RichHandler(
                console=console,
                show_time=False,
                show_level=False,
                show_path=False,
                markup=True,
                rich_tracebacks=True,
            )
            rich_handler.setFormatter(logging.Formatter("\\[[bold cyan]%(levelname)s[/bold cyan]] %(message)s"))
            self.logger.addHandler(rich_handler)

    def _scrub(self, message: str) -> str:
        """Scrub sensitive credentials from log text."""
        if not self.mask_sensitive or not isinstance(message, str):
            return str(message)
        scrubbed = message
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(self._scrub(message), **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(self._scrub(message), **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(self._scrub(message), **kwargs)

    def error(self, message: str, exc_info: Optional[BaseException] = None, **kwargs: Any) -> None:
        self.logger.error(self._scrub(message), exc_info=exc_info, **kwargs)

    def critical(
        self, message: str, exc_info: Optional[BaseException] = None, **kwargs: Any
    ) -> None:
        self.logger.critical(self._scrub(message), exc_info=exc_info, **kwargs)
