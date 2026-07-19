"""Geo location command handler."""

import argparse
from typing import Dict
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo
from ariadne.core.models import TargetEntity, TargetType


class GeoCommand(BaseCommand):
    """Handler for OpenStreetMap, reverse geocoding, and POI intelligence (`geo 'Istanbul'`)."""

    @property
    def command_name(self) -> str:
        return "geo"

    @property
    def description(self) -> str:
        return "Coğrafi koordinat veya şehir/bölge adı üzerinden harita ve konum istihbaratı yapar."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="GEO",
            purpose=self.description,
            short_usage="geo <location/coords>",
            usage_pattern='geo "<konum_veya_koordinat>" [-m key=val]',
            required_params=['<konum_veya_koordinat> : Şehir/yer adı veya enlem-boylam (örn: "Istanbul", "41.015 28.979")'],
            optional_params=["-m, --meta : Ek meta veri key=val formatında ekler"],
            examples=[
                "geo Istanbul",
                'geo "41.015 28.979"',
                'geo "Taksim Meydanı"',
            ],
            workflow=[
                "Coordinate Resolve (İsimden koordinat veya koordinattan adres ayrıştırma)",
                "Map (Bölge harita sınırları ve OpenStreetMap eşleşmesi)",
                "Nearby (Yakınlardaki kritik noktalar ve ilgi odatları POI analizi)",
                "Location Intelligence (Bölgesel risk ve istihbarat özeti oluşturma)",
            ],
            notes=[
                "Harita ve konum bulguları otomatik olarak [[Location_<id>]] notu altında toplanır.",
            ],
            error_missing_arg="geo komutu bir konum adı veya koordinat bekliyor.\nDoğru kullanım: geo Istanbul\nDetaylı yardım: help geo",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("location", help="Konum adı veya koordinat (örn: 'İstanbul' veya '41.01,29.00')")
        parser.add_argument(
            "--meta", "-m", action="append", help="Ek meta veri key=val formatında"
        )

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        meta_dict: Dict[str, str] = {"location": args.location}
        if getattr(args, "meta", None):
            for m in args.meta:
                if "=" in m:
                    k, v = m.split("=", 1)
                    meta_dict[k.strip()] = v.strip()

        clean_loc = "".join(c if c.isalnum() else "_" for c in args.location)[:30]
        target = TargetEntity(
            target_id=f"Geo_{clean_loc}",
            target_type=TargetType.CUSTOM,
            display_name=args.location,
            metadata=meta_dict,
        )
        await self.run_intelligence_command(target, context, command_override="geo")
