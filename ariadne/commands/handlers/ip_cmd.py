"""IP address command handler."""

import argparse
from typing import Dict
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo
from ariadne.core.models import TargetEntity, TargetType


class IPCommand(BaseCommand):
    """Handler for GeoIP, ASN, reverse DNS, and threat intelligence (`ip 8.8.8.8`)."""

    @property
    def command_name(self) -> str:
        return "ip"

    @property
    def description(self) -> str:
        return "IP adresi coğrafi konum (GeoIP), ASN/ISP bilgisi ve ters DNS sorgulaması yapar."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="IP",
            purpose=self.description,
            short_usage="ip <ip>",
            usage_pattern="ip <ip_adresi> [-m key=val]",
            required_params=["<ip_adresi> : IPv4 veya IPv6 adresi (örn: 8.8.8.8, 1.1.1.1)"],
            optional_params=["-m, --meta : Ek meta veri key=val formatında ekler"],
            examples=[
                "ip 8.8.8.8",
                "ip 1.1.1.1",
                "ip 185.199.108.153",
            ],
            workflow=[
                "ASN sorgulanır",
                "ISP tespit edilir",
                "Country ve City ayrıştırılır",
                "Coordinates (Enlem/Boylam) hesaplanır",
                "Reverse DNS ve Whois kayıtları incelenir",
                "Kullanıcı seçimiyle Export edilir",
            ],
            notes=[
                "IP koordinatları keşfedildiğinde otomatik olarak [[Location_<lat>_<lon>]] notuna bağlanır.",
                "Sorgu sonuçları 12 saat boyunca yerel önbellekte saklanır.",
            ],
            error_missing_arg="ip komutu bir IP adresi bekliyor.\nDoğru kullanım: ip 8.8.8.8\nDetaylı yardım: help ip",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ip", help="Hedef IP adresi (örn: 8.8.8.8)")
        parser.add_argument(
            "--meta", "-m", action="append", help="Ek meta veri key=val formatında"
        )

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        meta_dict: Dict[str, str] = {"ip": args.ip}
        if getattr(args, "meta", None):
            for m in args.meta:
                if "=" in m:
                    k, v = m.split("=", 1)
                    meta_dict[k.strip()] = v.strip()

        clean_ip = args.ip.replace(".", "_").replace(":", "_")
        target = TargetEntity(
            target_id=f"IP_{clean_ip}",
            target_type=TargetType.IP,
            display_name=args.ip,
            metadata=meta_dict,
        )
        await self.run_intelligence_command(target, context, command_override="ip")
