"""Domain command handler."""

import argparse
from typing import Dict
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo
from ariadne.core.models import TargetEntity, TargetType


class DomainCommand(BaseCommand):
    """Handler for domain DNS enumeration, WHOIS, SPF/DMARC, and technology discovery (`domain google.com`)."""

    @property
    def command_name(self) -> str:
        return "domain"

    @property
    def description(self) -> str:
        return "Alan adı DNS kayıtları (A, MX, NS, TXT), WHOIS ve ağ haritalaması yapar."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="DOMAIN",
            purpose=self.description,
            short_usage="domain <domain>",
            usage_pattern="domain <alan_adi> [-m key=val]",
            required_params=["<alan_adi> : Hedef alan adı (örn: google.com, github.com)"],
            optional_params=["-m, --meta : Ek meta veri key=val formatında ekler"],
            examples=[
                "domain google.com",
                "domain github.com",
                "domain kernel.org",
            ],
            workflow=[
                "DNS kayıtları (A, AAAA) çözümlenir",
                "WHOIS alan adı sahiplik ve süre verisi çekilir",
                "MX ve TXT (SPF/DMARC) güvenlik politikaları analiz edilir",
                "NS ve SOA sunucuları haritalanır",
                "CDN, ASN, IP ve coğrafi (Geo) vektörler listelenir",
            ],
            notes=[
                "Her alt alan adı veya çözümlenen IP [[IP_<adres>]] olarak kasa içinde birbirine bağlanır.",
            ],
            error_missing_arg="domain komutu bir alan adı bekliyor.\nDoğru kullanım: domain google.com\nDetaylı yardım: help domain",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("domain", help="Hedef alan adı (örn: google.com)")
        parser.add_argument(
            "--meta", "-m", action="append", help="Ek meta veri key=val formatında"
        )

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        meta_dict: Dict[str, str] = {"domain": args.domain}
        if getattr(args, "meta", None):
            for m in args.meta:
                if "=" in m:
                    k, v = m.split("=", 1)
                    meta_dict[k.strip()] = v.strip()

        clean_dom = args.domain.replace(".", "_")
        target = TargetEntity(
            target_id=f"Domain_{clean_dom}",
            target_type=TargetType.DOMAIN,
            display_name=args.domain,
            metadata=meta_dict,
        )
        await self.run_intelligence_command(target, context, command_override="domain")
