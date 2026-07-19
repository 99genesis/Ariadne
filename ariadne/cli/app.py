"""Ariadne CLI Entry Point & Command Router (`find new`, `find`, `target info`, `setup`).

Manages DI bootstrapping, plugin execution pipelines, SQLite indexer initialization,
and Rich terminal visualization.
"""

import argparse
import asyncio
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.formatted_text import HTML
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from ariadne.cli.i18n import I18nManager
from ariadne.cli.setup_wizard import SetupWizard
from ariadne.startup.startup_manager import StartupManager
from ariadne.commands.registry import CommandRegistry
from ariadne.commands.handlers import (
    DomainCommand,
    EmailCommand,
    GeoCommand,
    HelpCommand,
    ImageCommand,
    IPCommand,
    PhoneCommand,
    ProfileCommand,
    SetupCommand,
    TargetCommand,
    UsernameCommand,
)
import traceback
from pydantic import ValidationError
from ariadne.core.exceptions import (
    AriadneException,
    ConfigurationException,
    PluginException,
    ProviderException,
    SecurityException,
    StorageException,
)
from ariadne.config.config_manager import ConfigManager
from ariadne.config.secrets_manager import OSSecretsManager
from ariadne.core.container import container
from ariadne.core.interfaces import CommandContext, IEventBus, ILogger, INoteRepository, ISecretsManager
from ariadne.core.models import TargetEntity, TargetType
from ariadne.events.event_bus import AsyncEventBus
from ariadne.markdown.obsidian_exporter import ObsidianExporter
from ariadne.markdown.writer import MarkdownWriter
from ariadne.plugins.discovery import PluginDiscovery
from ariadne.plugins.loader import PluginLoader
from ariadne.plugins.manager import PluginManager
from ariadne.plugins.pipeline import ExecutionPipeline
from ariadne.plugins.registry import PluginRegistry
from ariadne.providers.ai.google_ai import GoogleAIProvider
from ariadne.providers.ai.openai_ai import OpenAIProvider
from ariadne.providers.ai.openrouter_ollama import OllamaProvider, OpenRouterProvider
from ariadne.providers.provider_manager import ProviderManager
from ariadne.storage.cache_manager import TwoTierCacheManager
from ariadne.storage.db.indexer import BackgroundIndexer
from ariadne.storage.db.repository import SQLiteNoteRepository
from ariadne.storage.logger import AriadneLogger


class InteractiveParseError(Exception):
    """Raised when InteractiveArgumentParser encounters a parse error or --help."""
    pass


class InteractiveArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that prevents sys.exit inside interactive REPL and shows Rich error panels."""

    def __init__(self, *args: Any, console: Optional[Console] = None, registry: Optional[CommandRegistry] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.console = console or Console()
        self.registry = registry

    def exit(self, status: int = 0, message: Optional[str] = None) -> None:
        if message:
            self.console.print(f"[yellow]{message}[/yellow]")
        raise InteractiveParseError()

    def error(self, message: str) -> None:
        suggestion_text = ""
        if self.registry and ("invalid choice" in message or "unrecognized arguments" in message):
            # Attempt to find what command the user might have meant
            words = message.replace("'", " ").replace(":", " ").split()
            for w in words:
                matches = self.registry.get_close_matches(w)
                if matches:
                    suggestion_text = "\n\n[bold yellow]Bunu mu demek istediniz?[/bold yellow]\n" + "\n".join(
                        f"  • [cyan]{m}[/cyan]" for m in matches
                    )
                    break

        error_content = f"[bold red]❌ Kullanım Hatası:[/bold red] {message}{suggestion_text}\n\n[dim]💡 Detaylı komut kılavuzu için '[bold white]help <komut>[/bold white]' veya genel liste için '[bold white]help[/bold white]' yazabilirsiniz.[/dim]"
        self.console.print(
            Panel.fit(
                error_content,
                border_style="red",
                title="Ariadne Terminal Hatası",
            )
        )
        raise InteractiveParseError()


class AriadneCLIApp:
    """Main CLI Application class coordinating all subsystems."""

    def __init__(self) -> None:
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        if hasattr(sys.stderr, "reconfigure"):
            try:
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        self.console = Console()
        self.config_manager = ConfigManager()
        self.i18n = I18nManager(current_lang=self.config_manager.config.system.language)
        self.command_registry = CommandRegistry()
        self.startup_manager = StartupManager(self.console)

    async def _bootstrap(self, force_setup: bool = False, interactive: bool = False) -> None:
        """Bootstrap DI container and load providers/plugins via StartupManager."""
        if interactive:
            await self.startup_manager.run_interactive_startup(self)
        else:
            await self.startup_manager.bootstrap_silent(self, force_setup=force_setup)

    def handle_runtime_error(self, exc: Exception, console: Console, is_debug: bool = False) -> None:
        """Render unexpected exceptions cleanly as a professional Rich error panel."""
        if isinstance(exc, ValidationError):
            operation = "Veri Doğrulama (Data Validation)"
            explanation = f"Model veya yapılandırma şeması geçersiz parametre içeriyor:\n{exc}"
            probable_cause = "Gerekli bir alan eksik veya geçersiz veri tipi sağlandı."
            recovery = "Komut parametrelerinizi veya yapılandırmanızı kontrol edin ('help <komut>')."
        elif isinstance(exc, PluginException):
            operation = "Eklenti Yürütme (Plugin Execution)"
            explanation = str(exc.message) if hasattr(exc, "message") else str(exc)
            probable_cause = "Modül çalışırken ağ hatası, hedef yanıt vermeme veya eksik bağımlılık oluştu."
            recovery = "Ağ/DNS bağlantınızı kontrol edin. Log seviyesini DEBUG yaparak logları inceleyin."
        elif isinstance(exc, ProviderException):
            operation = "Yapay Zeka / Servis Sağlayıcısı (AI Provider)"
            explanation = str(exc.message) if hasattr(exc, "message") else str(exc)
            probable_cause = "API anahtarı geçersiz, kota aşılmış veya sağlayıcı ağ bağlantısı başarısız oldu."
            recovery = "'setup' komutu ile API anahtarınızı ve sağlayıcı yapılandırmanızı kontrol edin."
        elif isinstance(exc, (ConfigurationException, SecurityException)):
            operation = "Yapılandırma & Güvenlik (Config & Security)"
            explanation = str(exc.message) if hasattr(exc, "message") else str(exc)
            probable_cause = "Ayarlar dosyası bozuk veya OS kilit kasasından şifreler okunamadı."
            recovery = "'setup' komutu ile ayarları sıfırlayın veya dosya izinlerini doğrulayın."
        elif isinstance(exc, StorageException):
            operation = "Veri Depolama & Kasa (Storage & Vault)"
            explanation = str(exc.message) if hasattr(exc, "message") else str(exc)
            probable_cause = "Obsidian kilit klasörü (.obsidian) veya SQLite veritabanı dosyasına yazılamıyor."
            recovery = "Kasa klasörünün izinlerini kontrol edin."
        elif isinstance(exc, (AttributeError, KeyError)):
            operation = "Sistem İçi Nesne/Veri Erişimi (Data Access)"
            explanation = str(exc)
            probable_cause = "Beklenmeyen veri yapısı veya eksik sözlük/nesne anahtarı."
            recovery = "Sistem yapılandırmasını kontrol edin veya geliştirici ekibine bildirin."
        else:
            operation = "Yürütme / Komut Hatası (Execution Error)"
            explanation = str(exc)
            probable_cause = "Sistem, ağ veya girdi kaynaklı beklenmeyen durum."
            recovery = "Sorun devam ederse log seviyesini DEBUG yaparak logları inceleyin."

        panel_content = (
            f"[bold red]❌ Çalışma Zamanı Hatası / Runtime Exception[/bold red]\n\n"
            f"[bold yellow]• İşlem (Operation):[/bold yellow] [white]{operation}[/white]\n"
            f"[bold yellow]• Kısa Açıklama:[/bold yellow] [white]{explanation}[/white]\n"
            f"[bold yellow]• Olası Neden:[/bold yellow] [dim white]{probable_cause}[/dim white]\n"
            f"[bold yellow]• Çözüm Önerisi:[/bold yellow] [cyan]{recovery}[/cyan]"
        )
        if is_debug or os.environ.get("ARIADNE_DEBUG", "") == "1":
            panel_content += f"\n\n[bold dim red]── Traceback (DEBUG Mode) ──[/bold dim red]\n[dim]{traceback.format_exc()}[/dim]"
        console.print()
        console.print(Panel.fit(panel_content, border_style="red"))

    async def run_interactive_shell(self, parser: argparse.ArgumentParser, subparsers: Optional[Any] = None) -> None:
        """Run continuous REPL interactive terminal shell with TAB autocomplete and Rich error handling."""
        await self._bootstrap(interactive=True)
        if subparsers is not None:
            self.command_registry.configure_subparsers(subparsers)
            if isinstance(parser, InteractiveArgumentParser):
                parser.console = self.console
                parser.registry = self.command_registry

        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]⚡ Ariadne OSINT Terminal[/bold cyan]\n"
                "[dim]Tek Terminalden Tüm Operasyon, Eklenti ve Obsidian Graf Yönetimi[/dim]\n"
                "[yellow]Komutları doğrudan yazabilirsiniz. TAB tuşuyla otomatik tamamlama aktiftir. Yardım için 'help' veya çıkış için 'exit' yazın.[/yellow]",
                border_style="cyan",
            )
        )

        session: Optional[Any] = None
        if PROMPT_TOOLKIT_AVAILABLE:
            try:
                from prompt_toolkit.history import FileHistory
                
                history_dir = Path.home() / ".ariadne"
                history_dir.mkdir(parents=True, exist_ok=True)
                history_file = history_dir / "history"
                
                session = PromptSession(history=FileHistory(str(history_file)))
            except Exception as e:
                self.console.print(f"[dim yellow]PromptSession fallback: {e}[/dim yellow]")
                session = None

        while True:
            try:
                vault_name = self.config_manager.config.system.vault_root.name
                user_input = ""

                if session and PROMPT_TOOLKIT_AVAILABLE:
                    completer_words = self.command_registry.get_command_names() + [
                        "exit",
                        "quit",
                        "clear",
                        "cls",
                        "help",
                    ]
                    completer = WordCompleter(words=completer_words, ignore_case=True)
                    prompt_html = HTML(f'<cyan><b>ariadne</b></cyan> [<green>{vault_name}</green>] > ')
                    user_input = await session.prompt_async(prompt_html, completer=completer)
                else:
                    user_input = Prompt.ask(f"[bold cyan]ariadne[/bold cyan] \\[[green]{vault_name}[/green]] > ")

                user_input = user_input.strip()
                if not user_input:
                    continue

                lower_input = user_input.lower()
                if lower_input in ("exit", "quit", "q", "çıkış", "cikis"):
                    self.console.print("[yellow]Ariadne terminalinden çıkılıyor. Güvenli günler![/yellow]")
                    break
                elif lower_input in ("clear", "cls", "temizle"):
                    os.system("cls" if os.name == "nt" else "clear")
                    self.console.print(
                        Panel.fit(
                            "[bold cyan]⚡ Ariadne OSINT Terminal — Interactive Shell[/bold cyan]\n"
                            "[yellow]Yardım için 'help' veya çıkış için 'exit' yazın.[/yellow]",
                            border_style="cyan",
                        )
                    )
                    continue
                elif lower_input in ("help", "yardım", "yardim", "?"):
                    # Dispatch directly to HelpCommand
                    user_input = "help"
                elif lower_input.startswith("lang "):
                    lang_code = lower_input.split(" ", 1)[1].strip()
                    self.i18n.set_language(lang_code)
                    self.config_manager.config.system.language = lang_code
                    self.config_manager.save_global_config(self.config_manager.config)
                    self.console.print(f"[bold green]✔ Dil '{lang_code}' olarak güncellendi.[/bold green]")
                    continue

                # Parse tokens using shlex
                try:
                    tokens = shlex.split(user_input, posix=False)
                    tokens = [t.strip('"').strip("'") for t in tokens]
                except Exception:
                    tokens = user_input.split()

                args = parser.parse_args(tokens)
                if not args.command:
                    continue

                context = CommandContext(
                    container=container,
                    logger=container.resolve(ILogger),
                    event_bus=container.resolve(IEventBus),
                    vault_name=self.config_manager.config.system.vault_root.name,
                    is_interactive=True,
                )
                await self.command_registry.execute_command(args.command, args, context)

            except InteractiveParseError:
                continue
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Ariadne terminalinden çıkılıyor...[/yellow]")
                break
            except Exception as exc:
                is_debug = getattr(self.config_manager.config.system, "log_level", "INFO").upper() == "DEBUG"
                self.handle_runtime_error(exc, self.console, is_debug)


def main() -> None:
    """CLI entry point."""
    is_interactive = len(sys.argv) <= 1
    parser_cls = InteractiveArgumentParser if is_interactive else argparse.ArgumentParser

    parser = parser_cls(description="Ariadne OSINT Framework CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    app = AriadneCLIApp()

    if is_interactive:
        try:
            asyncio.run(app.run_interactive_shell(parser, subparsers))
        except (KeyboardInterrupt, EOFError):
            pass
        return

    asyncio.run(app._bootstrap(interactive=False))
    app.command_registry.configure_subparsers(subparsers)
    args = parser.parse_args()
    if args.command:
        context = CommandContext(
            container=container,
            logger=container.resolve(ILogger),
            event_bus=container.resolve(IEventBus),
            vault_name=app.config_manager.config.system.vault_root.name,
            is_interactive=False,
        )
        try:
            asyncio.run(app.command_registry.execute_command(args.command, args, context))
        except Exception as exc:
            is_debug = getattr(app.config_manager.config.system, "log_level", "INFO").upper() == "DEBUG"
            app.handle_runtime_error(exc, app.console, is_debug)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
