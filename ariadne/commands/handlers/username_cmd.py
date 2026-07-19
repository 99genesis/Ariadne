"""Username command handler."""

import argparse
from typing import Dict
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo
from ariadne.core.models import TargetEntity, TargetType


class UsernameCommand(BaseCommand):
    """Handler for username enumeration and social profile discovery (`username torvalds`)."""

    @property
    def command_name(self) -> str:
        return "username"

    @property
    def description(self) -> str:
        return "Sosyal medya ve geliştirici platformlarında kullanıcı adı araması yapar."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="USERNAME",
            purpose=self.description,
            short_usage="username <username>",
            usage_pattern="username <username> [-m key=val]",
            required_params=["<username> : Hedef kullanıcı adı (örn: torvalds, endann)"],
            optional_params=["-m, --meta : Ek meta veri belirtir (örn: -m platform=github)"],
            examples=[
                "username endann",
                "username torvalds",
                "username johndoe",
            ],
            workflow=[
                "Sherlock tabanlı tarama başlar",
                "Desteklenen siteler taranır",
                "Sonuçlar terminale index halinde gelir",
                "Kullanıcı export edeceği sonuçları seçer",
                "Daha sonra Obsidian'a aktarılır",
            ],
            notes=[
                "Bulunan profiller otomatik olarak [[Username_<hedef>]] kasa klasörüne köprülenir.",
                "Önbellek (cache) devrededir; aynı kullanıcı adı 24 saat içinde tekrar taranırsa anlık gelir.",
            ],
            error_missing_arg="username komutu bir kullanıcı adı bekliyor.\nDoğru kullanım: username torvalds\nDetaylı yardım: help username",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("target", help="Hedef kullanıcı adı (örn: torvalds)")
        parser.add_argument(
            "--meta", "-m", action="append", help="Ek meta veri key=val formatında (örn: -m platform=github)"
        )

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        meta_dict: Dict[str, str] = {"username": args.target}
        if getattr(args, "meta", None):
            for m in args.meta:
                if "=" in m:
                    k, v = m.split("=", 1)
                    meta_dict[k.strip()] = v.strip()

        target = TargetEntity(
            target_id=f"Username_{args.target}",
            target_type=TargetType.USERNAME,
            display_name=args.target,
            metadata=meta_dict,
        )
        await self.run_intelligence_command(target, context, command_override="username")
