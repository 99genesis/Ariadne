"""Setup command handler."""

import argparse
from typing import Any
from rich.console import Console
from ariadne.commands.base import BaseCommand
from ariadne.cli.setup_wizard import SetupWizard
from ariadne.config.config_manager import ConfigManager
from ariadne.core.interfaces import CommandContext, CommandManualInfo, ILogger, ISecretsManager
from ariadne.cli.i18n import I18nManager


class SetupCommand(BaseCommand):
    """Handler for interactive setup wizard (`setup`)."""

    @property
    def command_name(self) -> str:
        return "setup"

    @property
    def description(self) -> str:
        return "Kurulum sihirbazını çalıştırır, dil seçimi ve API anahtarı yapılandırmasını yapar."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="SETUP",
            purpose=self.description,
            short_usage="setup",
            usage_pattern="setup",
            required_params=[],
            optional_params=[],
            examples=[
                "setup",
            ],
            workflow=[
                "Workspace (Obsidian kasa ve çalışma dizini seçimi/doğrulaması)",
                "Language (i18n dil tercihi ayarlama e.g. TR, EN, RU, ZH)",
                "AI Provider (Google Gemini, OpenAI, OpenRouter model seçimi)",
                "API Key (İlgili sağlayıcı anahtarlarını güvenli girişle alma)",
                "Proxy (Ağ veya Tor proxy yapılandırma seçenekleri)",
                "Secrets Manager (Anahtarları işletim sistemi Keyring kasasında şifreleyerek saklama)",
            ],
            notes=[
                "Kurulumu istediğiniz zaman 'setup' yazarak baştan başlatabilir veya konfigürasyonu yenileyebilirsiniz.",
            ],
            error_missing_arg="",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        pass

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        cfg_mgr: ConfigManager = context.container.resolve(ConfigManager)
        sec_mgr: ISecretsManager = context.container.resolve(ISecretsManager)
        logger: ILogger = context.container.resolve(ILogger)
        i18n = I18nManager(current_lang=cfg_mgr.config.system.language)

        wizard = SetupWizard(
            config_manager=cfg_mgr,
            secrets_manager=sec_mgr,
            i18n=i18n,
            console=Console(),
            logger=logger,
        )
        await wizard.run_wizard()
