"""Phone command handler."""

import argparse
from typing import Dict
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo
from ariadne.core.models import TargetEntity, TargetType


class PhoneCommand(BaseCommand):
    """Handler for phone number verification, carrier inference, and breach check (`phone +90555...`)."""

    @property
    def command_name(self) -> str:
        return "phone"

    @property
    def description(self) -> str:
        return "Telefon numarası doğrulama, operatör/ülke tespiti ve sızıntı analizi yapar."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="PHONE",
            purpose=self.description,
            short_usage="phone <phone>",
            usage_pattern="phone <numara> [-m key=val]",
            required_params=["<numara> : E.164 uluslararası formatta telefon numarası (örn: +905551234567)"],
            optional_params=["-m, --meta : Ek meta veri key=val formatında ekler"],
            examples=[
                "phone +905551234567",
                "phone +14155552671",
            ],
            workflow=[
                "Country (Ülke kodu ve bölge) tespiti yapılır",
                "Carrier (GSM Operatörü / Hat sağlayıcı) belirlenir",
                "Validation (Numara formatı ve aktiflik doğrulaması) gerçekleştirilir",
                "Leak Search (Bilinen veri sızıntılarında arama) yapılır",
            ],
            notes=[
                "E.164 formatı (+ ve ülke kodu) zorunludur.",
                "Tespit edilen sızıntılar [[Breach_Report]] veya [[Phone_<numara>]] altında Obsidian'a kaydedilir.",
            ],
            error_missing_arg="phone komutu E.164 formatında bir telefon numarası bekliyor.\nDoğru kullanım: phone +905551234567\nDetaylı yardım: help phone",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("phone", help="E.164 formatında telefon numarası (örn: +905551234567)")
        parser.add_argument(
            "--meta", "-m", action="append", help="Ek meta veri key=val formatında"
        )

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        meta_dict: Dict[str, str] = {"phone": args.phone}
        if getattr(args, "meta", None):
            for m in args.meta:
                if "=" in m:
                    k, v = m.split("=", 1)
                    meta_dict[k.strip()] = v.strip()

        clean_num = "".join(c for c in args.phone if c.isalnum() or c == "+")
        target = TargetEntity(
            target_id=f"Phone_{clean_num}",
            target_type=TargetType.PHONE,
            display_name=args.phone,
            metadata=meta_dict,
        )
        await self.run_intelligence_command(target, context, command_override="phone")
