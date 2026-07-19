"""Email command handler."""

import argparse
from typing import Dict
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo
from ariadne.core.models import TargetEntity, TargetType


class EmailCommand(BaseCommand):
    """Handler for email validation, MX check, Gravatar discovery, and leak intelligence (`email test@domain.com`)."""

    @property
    def command_name(self) -> str:
        return "email"

    @property
    def description(self) -> str:
        return "E-posta doğrulama, MX kaydı kontrolü, HIBP sızıntı denetimi ve Gravatar taraması."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="EMAIL",
            purpose=self.description,
            short_usage="email <email>",
            usage_pattern="email <eposta_adresi> [-m key=val]",
            required_params=["<eposta_adresi> : Hedef e-posta (örn: test@gmail.com, mail@test.com)"],
            optional_params=["-m, --meta : Ek meta veri key=val formatında ekler"],
            examples=[
                "email test@gmail.com",
                "email mail@test.com",
                "email admin@kernel.org",
            ],
            workflow=[
                "MX (Mail Exchange) sunucu kayıtları doğrulanır",
                "Gravatar profil fotoğrafları ve sosyal bağlantılar taranır",
                "HIBP (Have I Been Pwned) veritabanı sızıntı kontrolü yapılır",
                "Validation (Sözdizimi ve sunucu yanıtı doğrulaması) gerçekleştirilir",
            ],
            notes=[
                "E-posta sızıntıları ve bulguları [[Email_<adres>]] olarak kasa içinde indekslenir.",
            ],
            error_missing_arg="email komutu bir e-posta adresi bekliyor.\nDoğru kullanım: email test@gmail.com\nDetaylı yardım: help email",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("email", help="Hedef e-posta adresi (örn: test@linux.org)")
        parser.add_argument(
            "--meta", "-m", action="append", help="Ek meta veri key=val formatında"
        )

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        meta_dict: Dict[str, str] = {"email": args.email}
        if getattr(args, "meta", None):
            for m in args.meta:
                if "=" in m:
                    k, v = m.split("=", 1)
                    meta_dict[k.strip()] = v.strip()

        clean_mail = args.email.replace("@", "_at_").replace(".", "_")
        target = TargetEntity(
            target_id=f"Email_{clean_mail}",
            target_type=TargetType.EMAIL,
            display_name=args.email,
            metadata=meta_dict,
        )
        await self.run_intelligence_command(target, context, command_override="email")
