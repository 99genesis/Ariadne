"""Interactive Setup Wizard for Ariadne OSINT Framework.

Presents default English welcome banner, prompts immediate language selection,
configures vault paths, AI providers, proxy settings, and stores secrets securely.
"""

from pathlib import Path
from typing import Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ariadne.cli.i18n import I18nManager
from ariadne.config.config_manager import ConfigManager
from ariadne.config.schema import AriadneGlobalConfig
from ariadne.core.interfaces import ISecretsManager


class SetupWizard:
    """Guided terminal configuration wizard."""

    def __init__(
        self,
        config_manager: ConfigManager,
        secrets_manager: ISecretsManager,
        i18n: I18nManager,
        console: Optional[Console] = None,
        logger: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        self.config_manager = config_manager
        self.secrets_manager = secrets_manager
        self.i18n = i18n
        self.logger = logger
        import sys
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        self.console = console or Console()

    def _clean_input_buffer(self) -> None:
        """Clear keyboard/input buffer on Windows to prevent leftover newlines from auto-skipping prompts."""
        import sys
        if sys.platform == "win32":
            try:
                import msvcrt
                while msvcrt.kbhit():
                    msvcrt.getwch()
            except Exception:
                pass

    async def run(self) -> AriadneGlobalConfig:
        """Alias for run_wizard delegating execution cleanly."""
        return await self.run_wizard()

    async def run_wizard(self) -> AriadneGlobalConfig:
        """Run step-by-step interactive configuration setup."""
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]Welcome to Ariadne OSINT Framework[/bold cyan]\n"
                "[dim]Enterprise Asynchronous Intelligence & Obsidian Graph Engine[/dim]",
                border_style="cyan",
            )
        )

        # 1. Immediate Language Selection
        self.console.print("[bold yellow]Please select your interface language right now:[/bold yellow]")
        self.console.print("  [bold cyan]1.[/bold cyan] English (en)")
        self.console.print("  [bold cyan]2.[/bold cyan] Русский (ru)")
        self.console.print("  [bold cyan]3.[/bold cyan] 中文 (zh)")
        self.console.print("  [bold cyan]4.[/bold cyan] Türkçe (tr)")

        self._clean_input_buffer()
        lang_choice = Prompt.ask("Select Language [1-4]", choices=["1", "2", "3", "4", "en", "ru", "zh", "tr"], default="1")
        lang_map = {"1": "en", "2": "ru", "3": "zh", "4": "tr"}
        selected_lang = lang_map.get(lang_choice, lang_choice.lower())
        self.i18n.set_language(selected_lang)

        self.console.print()
        self.console.print(
            f"[bold green]{self.i18n.get('setup_title')}[/bold green]"
        )
        self.console.print("─" * 60)

        # 2. Vault Root Configuration
        default_vault = "Ariadne_Workspace"
        self._clean_input_buffer()
        vault_input = Prompt.ask(self.i18n.get("prompt_vault_root"), default=default_vault)
        vault_path = Path(vault_input)

        # 3. Primary AI Provider Selection
        self.console.print()
        self.console.print(f"[bold cyan]{self.i18n.get('prompt_ai_provider')}:[/bold cyan]")
        self.console.print("  [1] Google AI Studio / Gemini 2.5 Pro & Flash Latest (Recommended)")
        self.console.print("  [2] OpenAI GPT-4o / Vision")
        self.console.print("  [3] OpenRouter Multi-Cloud Aggregator")
        self.console.print("  [4] Ollama Local Offline (GGUF)")

        self._clean_input_buffer()
        provider_choice = Prompt.ask("Select AI Provider [1-4]", choices=["1", "2", "3", "4"], default="1")
        provider_map = {"1": "google_ai", "2": "openai", "3": "openrouter", "4": "ollama"}
        active_provider = provider_map[provider_choice]

        # Prompt for API Key
        if active_provider != "ollama":
            self._clean_input_buffer()
            api_key = Prompt.ask(
                self.i18n.get("prompt_api_key", provider=active_provider.upper()),
                password=True,
                default="",
            )
            if api_key.strip():
                await self.secrets_manager.set_secret(f"{active_provider}_api_key", api_key.strip())
                self.console.print("[dim green]✔ API key securely stored.[/dim green]")

        # 4. Network Proxy Configuration
        self.console.print()
        self._clean_input_buffer()
        proxy_enabled = Confirm.ask(self.i18n.get("prompt_proxy_enabled"), default=False)
        proxy_url = None
        if proxy_enabled:
            self._clean_input_buffer()
            proxy_url = Prompt.ask(
                self.i18n.get("prompt_proxy_url"), default="http://127.0.0.1:8080"
            )

        # Save Configuration
        new_config = AriadneGlobalConfig()
        new_config.system.language = selected_lang
        new_config.system.vault_root = vault_path
        new_config.providers.active_ai_provider = active_provider
        new_config.providers.active_vision_model = "gemini-flash-latest"
        new_config.providers.fallback_models = ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.0-flash"]
        new_config.network.proxy.enabled = proxy_enabled
        if proxy_url:
            new_config.network.proxy.url = proxy_url

        self.config_manager.save_global_config(new_config)
        vault_path.mkdir(parents=True, exist_ok=True)

        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold green]{self.i18n.get('setup_complete', path=str(self.config_manager.config_file))}[/bold green]",
                border_style="green",
            )
        )
        return new_config
