"""Help command handler."""

import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from ariadne.commands.base import BaseCommand
from ariadne.commands.registry import CommandRegistry
from ariadne.core.interfaces import CommandContext, CommandManualInfo


class HelpCommand(BaseCommand):
    """Handler displaying dynamic help table generated from CommandRegistry (`help`)."""

    @property
    def command_name(self) -> str:
        return "help"

    @property
    def description(self) -> str:
        return "Tüm komutları ve açıklamalarını veya tek bir komutun detaylı kılavuzunu (Manual) listeler."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="HELP",
            purpose=self.description,
            short_usage="help [komut]",
            usage_pattern="help [komut_adi]",
            required_params=[],
            optional_params=["[komut_adi] : Detaylı kullanım kılavuzu istenen komutun adı (örn: username, image, ip)"],
            examples=[
                "help",
                "help username",
                "help image",
                "help ip",
                "help domain",
            ],
            workflow=[
                "Eğer parametre verilmediyse tüm komutların dinamik tablosu ve örnek kullanımları listelenir",
                "Eğer komut adı verildse (örn: help username) o komutun tüm ICommand metadatası ve kullanım kılavuzu açılır",
            ],
            notes=[
                "Yardım sistemi tamamen dinamiktir; sisteme eklenen her yeni eklenti veya komut anında kılavuza yansır.",
            ],
            error_missing_arg="",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "target_cmd",
            nargs="?",
            default=None,
            help="Detaylı kılavuzunu görüntülemek istediğiniz komut adı (örn: username)",
        )

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        console = Console()
        try:
            registry: CommandRegistry = context.container.resolve(CommandRegistry)
        except Exception:
            console.print("[yellow]Yardım tablosu oluşturulurken kayıt listesi bulunamadı.[/yellow]")
            return

        target_cmd = getattr(args, "target_cmd", None)
        if target_cmd:
            cmd = registry.get_command(target_cmd)
            if not cmd:
                matches = registry.get_close_matches(target_cmd)
                suggestion_str = ""
                if matches:
                    suggestion_str = "\n\n[bold yellow]Bunu mu demek istediniz?[/bold yellow]\n" + "\n".join(
                        f"  • [cyan]{m}[/cyan]" for m in matches
                    )
                console.print(
                    Panel.fit(
                        f"[bold red]❌ Komut bulunamadı: '{target_cmd}'[/bold red]{suggestion_str}",
                        border_style="red",
                        title="Bilinmeyen Komut",
                    )
                )
                return

            # Display full manual info
            info = getattr(cmd, "manual_info", None)
            if not info:
                console.print(f"[yellow]'{cmd.command_name}' komutu için kılavuz bilgisi bulunamadı.[/yellow]")
                return

            console.print()
            header_text = f"[bold cyan]─── {info.name.upper()} KOMUT KILAVUZU (MANUAL) ───[/bold cyan]\n\n"
            header_text += f"[bold white]Açıklama:[/bold white]\n  {info.purpose}\n\n"
            header_text += f"[bold white]Kullanım:[/bold white]\n  [bold yellow]{info.usage_pattern}[/bold yellow]\n"

            if info.required_params:
                header_text += "\n[bold white]Gerekli Parametreler:[/bold white]\n"
                for p in info.required_params:
                    header_text += f"  • {p}\n"

            if info.optional_params:
                header_text += "\n[bold white]Opsiyonel Parametreler:[/bold white]\n"
                for p in info.optional_params:
                    header_text += f"  • {p}\n"

            if info.examples:
                header_text += "\n[bold white]Örnek Kullanımlar:[/bold white]\n"
                for ex in info.examples:
                    header_text += f"  [green]ariadne >[/green] [bold cyan]{ex}[/bold cyan]\n"

            if info.workflow:
                header_text += "\n[bold white]Ne Olur? / Yapılan İşlemler:[/bold white]\n"
                for wf in info.workflow:
                    header_text += f"  • {wf}\n"

            if info.notes:
                header_text += "\n[bold white]Notlar:[/bold white]\n"
                for nt in info.notes:
                    header_text += f"  💡 {nt}\n"

            console.print(Panel(header_text.strip(), border_style="cyan", title=f"Help: {info.name.lower()}"))
            console.print()
        else:
            # General help table + examples
            console.print()
            console.print(registry.get_help_table())

            examples_text = ""
            for cmd in registry.list_commands():
                info = getattr(cmd, "manual_info", None)
                if info and info.examples:
                    examples_text += f"  [green]ariadne >[/green] [bold cyan]{info.examples[0]}[/bold cyan]\n"
                else:
                    examples_text += f"  [green]ariadne >[/green] [bold cyan]{cmd.command_name}[/bold cyan]\n"

            console.print(
                Panel.fit(
                    f"[bold yellow]Örnek Kullanımlar:[/bold yellow]\n\n{examples_text.strip()}\n\n"
                    f"[dim]Herhangi bir komutun tam kılavuzunu görmek için '[bold white]help <komut_adı>[/bold white]' yazın (örn: 'help username').[/dim]",
                    border_style="yellow",
                    title="Ariadne OSINT Örnekler",
                )
            )
            console.print()
