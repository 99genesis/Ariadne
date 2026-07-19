"""Command Registry for managing and dispatching CLI commands dynamically."""

import argparse
import difflib
from typing import Any, Dict, List, Optional
from rich.table import Table

from ariadne.core.interfaces import CommandContext, ICommand, ILogger


class CommandRegistry:
    """Registry maintaining active CLI command handlers and generating dynamic help tables."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        self.logger = logger
        self._commands: Dict[str, ICommand] = {}

    def register_command(self, cmd: ICommand) -> None:
        """Register an ICommand instance."""
        self._commands[cmd.command_name.strip().lower()] = cmd
        if self.logger:
            self.logger.debug(f"Registered command handler: {cmd.command_name}")

    def get_command(self, name: str) -> Optional[ICommand]:
        """Retrieve command instance by name."""
        return self._commands.get(name.strip().lower())

    def list_commands(self) -> List[ICommand]:
        """List all registered commands sorted alphabetically."""
        return [self._commands[k] for k in sorted(self._commands.keys())]

    def get_command_names(self) -> List[str]:
        """Return a sorted list of all registered command names."""
        return sorted(self._commands.keys())

    def get_close_matches(self, query: str, n: int = 3, cutoff: float = 0.4) -> List[str]:
        """Return close matches for fuzzy suggestion when an unknown command is entered."""
        return difflib.get_close_matches(query.strip().lower(), self.get_command_names(), n=n, cutoff=cutoff)

    def configure_subparsers(self, subparsers: Any) -> None:
        """Configure argparse subparsers for all registered commands."""
        for name, cmd in sorted(self._commands.items()):
            parser = subparsers.add_parser(name, help=cmd.description)
            cmd.configure_parser(parser)

    async def execute_command(
        self, command_name: str, args: argparse.Namespace, context: CommandContext
    ) -> None:
        """Dispatch execution to the registered command handler."""
        cmd = self.get_command(command_name)
        if not cmd:
            raise ValueError(f"Unknown command: {command_name}")

        try:
            from ariadne.core.interfaces import INoteRepository, IWorkspaceManager
            wm = context.container.resolve(IWorkspaceManager)
            if wm:
                active = wm.get_active_target()
                paths = wm.get_target_paths(active)

                if paths and paths.target_name != "Ariadne_General":
                    context.active_target = paths.target_name
                    context.workspace_paths = paths
                    context.vault_root = paths.vault_dir.parent
                    context.vault_name = paths.vault_dir.name

                    # Scope repository and cache to target
                    try:
                        repo = context.container.resolve(INoteRepository)
                        if hasattr(repo, "set_target_db"):
                            repo.set_target_db(paths.db_path)
                        else:
                            repo.db_path = paths.db_path
                            if hasattr(repo, "_init_db"):
                                repo._init_db()
                    except Exception:
                        pass

                    try:
                        cache = context.container.resolve("ICacheManager")
                        if hasattr(cache, "set_target_cache_dir"):
                            cache.set_target_cache_dir(paths.cache_dir)
                        else:
                            cache.cache_dir = paths.cache_dir
                    except Exception:
                        pass
        except Exception as exc:
            if self.logger:
                self.logger.debug(f"Workspace routing skipped or failed: {exc}")

        await cmd.execute(args, context)

    def get_help_table(self) -> Table:
        """Generate a Rich Table summarizing all registered commands and their descriptions."""
        table = Table(title="Ariadne Terminal Komutları (Command Registry)", border_style="cyan")
        table.add_column("Komut", style="bold yellow")
        table.add_column("Açıklama", style="green")
        table.add_column("Kısa kullanım", style="blue")

        for cmd in self.list_commands():
            short_usage = getattr(cmd, "manual_info", None)
            usage_str = short_usage.short_usage if short_usage else f"{cmd.command_name} <args>"
            table.add_row(cmd.command_name, cmd.description, usage_str)

        return table
