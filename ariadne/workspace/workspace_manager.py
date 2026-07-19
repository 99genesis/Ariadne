"""Central Workspace Manager for multi-target OSINT investigations.

Manages target workspace creation, switching, persistence, extensible folder hierarchies,
and scoped directory resolution without global static variables.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from ariadne.core.exceptions import StorageException
from ariadne.core.interfaces import ILogger
from ariadne.workspace.models import TargetWorkspaceConfig, TargetWorkspacePaths


class WorkspaceManager:
    """Manages multi-target workspace lifecycle, directory structure, and active context routing."""

    def __init__(self, workspace_root: Path, logger: Optional[ILogger] = None) -> None:
        """Initialize WorkspaceManager.

        Args:
            workspace_root: Root directory of the entire Ariadne workspace (e.g. Ariadne_Workspace).
            logger: Optional logger instance.
        """
        self.workspace_root = Path(workspace_root)
        self.targets_dir = self.workspace_root / "Targets"
        self.active_target_file = self.targets_dir / ".active_target"
        self.logger = logger
        self.targets_dir.mkdir(parents=True, exist_ok=True)

    def get_active_target(self) -> Optional[str]:
        """Get currently active target name from persistence file."""
        if not self.active_target_file.exists():
            return None
        try:
            name = self.active_target_file.read_text(encoding="utf-8").strip()
            if name and (self.targets_dir / name).exists():
                return name
            return None
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Failed to read active target file: {exc}")
            return None

    def switch_target(self, target_name: str) -> bool:
        """Switch active target to the specified name. Creates target if missing."""
        clean_name = target_name.strip()
        if not clean_name:
            raise ValueError("Target name cannot be empty.")

        target_path = self.targets_dir / clean_name
        if not target_path.exists():
            self.create_target(clean_name)

        try:
            self.targets_dir.mkdir(parents=True, exist_ok=True)
            self.active_target_file.write_text(clean_name, encoding="utf-8")
            if self.logger:
                self.logger.info(f"Switched active target to '{clean_name}'")
            return True
        except Exception as exc:
            raise StorageException(
                message=f"Failed to switch active target to '{clean_name}': {exc}",
                details={"error": str(exc)},
            )

    def create_target(
        self,
        target_name: str,
        description: str = "",
        aliases: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> TargetWorkspacePaths:
        """Create a new extensible target workspace folder hierarchy and config.json."""
        clean_name = target_name.strip()
        if not clean_name:
            raise ValueError("Target name cannot be empty.")

        target_root = self.targets_dir / clean_name
        paths = TargetWorkspacePaths(
            target_name=clean_name,
            target_root=target_root,
            vault_dir=target_root / "Vault",
            db_path=target_root / "notes.db",
            cache_dir=target_root / "Cache",
            reports_dir=target_root / "Reports",
            attachments_dir=target_root / "Attachments",
            entities_dir=target_root / "Entities",
            relations_dir=target_root / "Relations",
            timeline_dir=target_root / "Timeline",
            history_dir=target_root / "History",
            config_file=target_root / "config.json",
        )

        try:
            for d in [
                paths.target_root,
                paths.vault_dir,
                paths.cache_dir,
                paths.reports_dir,
                paths.attachments_dir,
                paths.entities_dir,
                paths.relations_dir,
                paths.timeline_dir,
                paths.history_dir,
            ]:
                d.mkdir(parents=True, exist_ok=True)

            # Ensure .obsidian exists inside Vault for clean Obsidian compatibility
            (paths.vault_dir / ".obsidian").mkdir(parents=True, exist_ok=True)

            if not paths.config_file.exists():
                config = TargetWorkspaceConfig(
                    target_name=clean_name,
                    description=description,
                    aliases=aliases or [],
                    tags=tags or [],
                )
                paths.config_file.write_text(config.model_dump_json(indent=2), encoding="utf-8")

            if self.logger:
                self.logger.info(f"Created target workspace hierarchy for '{clean_name}' at {target_root}")
            return paths
        except Exception as exc:
            raise StorageException(
                message=f"Failed to create target workspace structure for '{clean_name}': {exc}",
                details={"error": str(exc)},
            )

    def get_target_paths(self, target_name: Optional[str] = None) -> TargetWorkspacePaths:
        """Get directory paths for a target. Defaults to active target or root fallback."""
        t_name = target_name or self.get_active_target()
        if not t_name:
            # Fallback to general workspace root if no target is active
            return TargetWorkspacePaths(
                target_name="Ariadne_General",
                target_root=self.workspace_root,
                vault_dir=self.workspace_root,
                db_path=self.workspace_root / "notes.db",
                cache_dir=self.workspace_root / "Cache",
                reports_dir=self.workspace_root / "Reports",
                attachments_dir=self.workspace_root / "Attachments",
                entities_dir=self.workspace_root / "Entities",
                relations_dir=self.workspace_root / "Relations",
                timeline_dir=self.workspace_root / "Timeline",
                history_dir=self.workspace_root / "History",
                config_file=self.workspace_root / "config.json",
            )

        target_root = self.targets_dir / t_name
        if not target_root.exists():
            return self.create_target(t_name)

        return TargetWorkspacePaths(
            target_name=t_name,
            target_root=target_root,
            vault_dir=target_root / "Vault",
            db_path=target_root / "notes.db",
            cache_dir=target_root / "Cache",
            reports_dir=target_root / "Reports",
            attachments_dir=target_root / "Attachments",
            entities_dir=target_root / "Entities",
            relations_dir=target_root / "Relations",
            timeline_dir=target_root / "Timeline",
            history_dir=target_root / "History",
            config_file=target_root / "config.json",
        )

    def get_target_config(self, target_name: str) -> Optional[TargetWorkspaceConfig]:
        """Load and validate config.json for a target."""
        target_dir = self.targets_dir / target_name
        config_path = target_dir / "config.json"
        if not config_path.exists():
            if target_dir.is_dir():
                # Self-heal missing config.json for existing target folder
                config = TargetWorkspaceConfig(target_name=target_name, metadata={})
                try:
                    self.save_target_config(config)
                except Exception:
                    pass
                return config
            return None
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return TargetWorkspaceConfig.model_validate(data)
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Failed loading target config for '{target_name}': {exc}")
            if target_dir.is_dir():
                # Return in-memory fallback to prevent NoneType errors when JSON is corrupted
                return TargetWorkspaceConfig(target_name=target_name, metadata={})
            return None

    def save_target_config(self, config: TargetWorkspaceConfig) -> None:
        """Save target configuration back to config.json with updated_at timestamp."""
        config.updated_at = datetime.now(timezone.utc).isoformat()
        config_path = self.targets_dir / config.target_name / "config.json"
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        except Exception as exc:
            raise StorageException(
                message=f"Failed saving target config for '{config.target_name}': {exc}",
                details={"error": str(exc)},
            )

    def list_targets(self) -> List[Dict[str, Any]]:
        """List summary info for all existing targets sorted alphabetically."""
        if not self.targets_dir.exists():
            return []

        results: List[Dict[str, Any]] = []
        for p in sorted(self.targets_dir.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                cfg = self.get_target_config(p.name)
                db_path = p / "notes.db"
                db_size = db_path.stat().st_size if db_path.exists() else 0
                results.append({
                    "name": p.name,
                    "created_at": cfg.created_at if (cfg and cfg.created_at) else "Unknown",
                    "updated_at": cfg.updated_at if (cfg and cfg.updated_at) else "Unknown",
                    "last_scan": cfg.last_scan if (cfg and cfg.last_scan) else "Never",
                    "favorite": cfg.favorite if (cfg and cfg.favorite is not None) else False,
                    "tags": cfg.tags if (cfg and cfg.tags is not None) else [],
                    "description": cfg.description if (cfg and cfg.description is not None) else "",
                    "metadata": cfg.metadata if (cfg and cfg.metadata is not None) else {},
                    "db_size_bytes": db_size,
                })
        return results

    def delete_target(self, target_name: str) -> bool:
        """Delete target workspace directory safely."""
        target_path = self.targets_dir / target_name
        if not target_path.exists():
            return False

        try:
            shutil.rmtree(target_path, ignore_errors=False)
            if self.get_active_target() == target_name:
                if self.active_target_file.exists():
                    self.active_target_file.unlink()
            if self.logger:
                self.logger.info(f"Deleted target workspace '{target_name}'")
            return True
        except Exception as exc:
            raise StorageException(
                message=f"Failed deleting target workspace '{target_name}': {exc}",
                details={"error": str(exc)},
            )

    def ensure_target_workspace(self, target_id: str) -> TargetWorkspacePaths:
        """Ensure a workspace exists for target_id and make it active if requested."""
        clean_id = target_id.strip()
        if not clean_id:
            raise ValueError("Target ID cannot be empty.")

        target_path = self.targets_dir / clean_id
        if not target_path.exists():
            self.create_target(clean_id)

        self.switch_target(clean_id)
        return self.get_target_paths(clean_id)
