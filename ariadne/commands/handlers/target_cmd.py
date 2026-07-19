"""Target management command handler supporting Multi-Target Workspaces and Intelligence Dashboard."""

import argparse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo, INoteRepository, IWorkspaceManager


from typing import Any


def _format_ts(ts: Any, default: str) -> str:
    """Null-safe timestamp formatting helper preventing NoneType errors."""
    if not ts or not isinstance(ts, str) or ts in ("Unknown", "Never"):
        return default if ts != "Never" else "Never"
    return ts[:19].replace("T", " ")


class TargetCommand(BaseCommand):
    """Handler for target workspace lifecycle and intelligence summary dashboard (`target <action> [target_name]`)."""

    @property
    def command_name(self) -> str:
        return "target"

    @property
    def description(self) -> str:
        return "Çoklu hedef çalışma alanı yönetimi (create, switch, current, list, delete, info)."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="TARGET",
            purpose=self.description,
            short_usage="target <create|switch|current|list|delete|info> [hedef_adi]",
            usage_pattern="target <action> [hedef_adi]",
            required_params=[
                "action : Alt işlem (create, switch, current, list, delete, info)",
            ],
            optional_params=[
                "hedef_adi : Hedef kimliği (create, switch, delete ve info için zorunlu/opsiyonel)",
            ],
            examples=[
                "target create endann",
                "target switch endann",
                "target current",
                "target list",
                "target delete endann",
                "target info endann",
            ],
            workflow=[
                "Multi-Target Workspace yöneticisi (WorkspaceManager) ile yalıtılmış kasalar yönetilir",
                "create : Hedefe özel Vault, notes.db, Cache, Reports ve config.json oluşturur",
                "switch : Aktif hedefi değiştirerek tüm boru hattı akışını o hedefe yönlendirir",
                "current : Aktif hedefi ve yalıtılmış dizin yollarını ekrana basar",
                "list : Kayıtlı tüm hedefleri, not sayılarını ve veritabanı boyutlarını listeler",
                "delete : Onay alarak hedef çalışma alanını temizler",
                "info : Hedefin SQLite veritabanı üzerindeki istihbarat özet tablosunu basar",
            ],
            notes=[
                "Hedef çalışma alanları tamamen yalıtılmış olup bir hedefin verisi diğerine karışmaz.",
            ],
            error_missing_arg="target komutu geçerli bir alt işlem bekliyor (create, switch, current, list, delete, info).\nDetaylı yardım: help target",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("action", help="İşlem türü (create, switch, current, list, delete, info)")
        parser.add_argument("target_name", nargs="?", default=None, help="Hedef adı (örn: endann, torvalds)")

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        console = Console()
        action = args.action.lower()
        wm = context.container.resolve(IWorkspaceManager)

        if action == "create":
            if not args.target_name:
                console.print("[bold red]Hata: 'target create' komutu için hedef adı belirtilmelidir (örn: target create endann)[/bold red]")
                return
            paths = wm.create_target(args.target_name)
            console.print(
                Panel.fit(
                    f"[bold green]✔ Hedef Çalışma Alanı Oluşturuldu: {paths.target_name}[/bold green]\n\n"
                    f"• Vault : [cyan]{paths.vault_dir}[/cyan]\n"
                    f"• SQLite : [cyan]{paths.db_path}[/cyan]\n"
                    f"• Cache : [cyan]{paths.cache_dir}[/cyan]\n"
                    f"• Config : [cyan]{paths.config_file}[/cyan]",
                    title="🎯 Target Workspace Created",
                    border_style="green",
                )
            )

        elif action == "switch":
            if not args.target_name:
                console.print("[bold red]Hata: 'target switch' komutu için hedef adı belirtilmelidir (örn: target switch endann)[/bold red]")
                return
            wm.switch_target(args.target_name)
            paths = wm.get_target_paths(args.target_name)
            console.print(
                Panel.fit(
                    f"[bold green]✔ Aktif Hedef Değiştirildi: {args.target_name}[/bold green]\n"
                    f"Tüm istihbarat operasyonları artık bu hedefin kasasına ({paths.vault_dir.name}) yazılacak.",
                    title="⚡ Target Switched",
                    border_style="cyan",
                )
            )

        elif action == "current":
            active = wm.get_active_target()
            if not active:
                console.print(
                    Panel.fit(
                        "[yellow]Şu anda aktif bir hedef çalışma alanı seçilmemiş.[/yellow]\n"
                        "Genel çalışma alanı veya varsayılan dizinler aktif. Hedef seçmek için: [bold cyan]target switch <hedef>[/bold cyan]",
                        title="Aktif Hedef (Active Target)",
                        border_style="yellow",
                    )
                )
            else:
                paths = wm.get_target_paths(active)
                console.print(
                    Panel.fit(
                        f"[bold cyan]Aktif Hedef (Active Target): {active}[/bold cyan]\n\n"
                        f"• Kasa (Vault) : [green]{paths.vault_dir}[/green]\n"
                        f"• Veritabanı : [green]{paths.db_path}[/green]\n"
                        f"• Raporlar : [green]{paths.reports_dir}[/green]",
                        title="🎯 Current Target Workspace",
                        border_style="cyan",
                    )
                )

        elif action == "list":
            targets = wm.list_targets()
            if not targets:
                console.print("[yellow]Henüz oluşturulmuş bir hedef çalışma alanı bulunmuyor. Oluşturmak için: target create <hedef>[/yellow]")
                return

            active = wm.get_active_target()
            table = Table(title="Ariadne Hedef Çalışma Alanları (Multi-Target Workspaces)", border_style="cyan")
            table.add_column("Durum", justify="center", style="bold")
            table.add_column("Hedef Adı", style="bold yellow")
            table.add_column("Oluşturulma Tarihi", style="green")
            table.add_column("Son Tarama", style="blue")
            table.add_column("DB Boyutu", justify="right", style="magenta")

            for t in targets:
                is_active = (t["name"] == active)
                status_icon = "[bold green]✔ ACTIVE[/bold green]" if is_active else "[dim]inactive[/dim]"
                size_kb = t["db_size_bytes"] / 1024.0
                size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024.0:.2f} MB"
                table.add_row(
                    status_icon,
                    t["name"],
                    _format_ts(t.get("created_at"), "Unknown"),
                    _format_ts(t.get("last_scan"), "Never"),
                    size_str,
                )
            console.print()
            console.print(table)

        elif action == "delete":
            if not args.target_name:
                console.print("[bold red]Hata: 'target delete' komutu için silinecek hedef adı belirtilmelidir.[/bold red]")
                return
            if context.is_interactive:
                confirmed = Confirm.ask(f"[bold red]UYARI:[/bold red] '{args.target_name}' hedefini ve tüm kasasını/verilerini silmek istediğinize emin misiniz?", default=False)
                if not confirmed:
                    console.print("[yellow]Silme işlemi kullanıcı tarafından iptal edildi.[/yellow]")
                    return

            success = wm.delete_target(args.target_name)
            if success:
                console.print(f"[bold green]✔ '{args.target_name}' hedefine ait tüm veriler ve kasa silindi.[/bold green]")
            else:
                console.print(f"[bold red]Hata: '{args.target_name}' adında bir çalışma alanı bulunamadı.[/bold red]")

        elif action == "info":
            target_name = args.target_name or wm.get_active_target()
            if not target_name:
                console.print("[bold red]Hata: 'target info' için bir hedef adı belirtilmeli veya aktif hedef seçilmiş olmalıdır.[/bold red]")
                return

            repo = context.container.resolve(INoteRepository)
            paths = wm.get_target_paths(target_name)
            stats = await repo.get_target_summary_stats(paths.vault_dir.name, target_name)
            if stats["total_notes"] == 0:
                stats = await repo.get_target_summary_stats(target_name, target_name)

            console.print()
            # 1. Overview Table
            overview_table = Table(title=f"🎯 Intelligence Summary Dashboard: [bold cyan]{target_name}[/bold cyan]", border_style="cyan")
            overview_table.add_column("Metrik / Kategori (Metric)", style="bold yellow")
            overview_table.add_column("Değer / Dağılım (Value / Breakdown)", style="bold green")

            overview_table.add_row("Çalışma Alanı (Workspace)", f"[bold cyan]{target_name}[/bold cyan]")
            overview_table.add_row("Kasa Dizini (Vault Dir)", str(paths.vault_dir.name))
            overview_table.add_row("Toplam Keşfedilen Bulgu (Total Notes)", f"[bold green]{stats.get('total_notes', 0)}[/bold green]")
            overview_table.add_row("Ortalama Güven Skoru (Avg. Confidence)", f"[bold magenta]{stats.get('average_confidence', 0.0) * 100:.1f}%[/bold magenta]")

            # Investigated Scans / Targets
            inv_targets = stats.get("investigated_targets", {})
            if inv_targets:
                overview_table.add_section()
                overview_table.add_row("[bold cyan]İstihbarat Sorguları (Investigated Scans)[/bold cyan]", "")
                for t_id, count in inv_targets.items():
                    overview_table.add_row(f"  • [yellow]{t_id}[/yellow]", f"[bold green]{count} bulgu[/bold green]")

            # Entity Breakdown
            by_ent = stats.get("entity_counts", {})
            if by_ent:
                overview_table.add_section()
                overview_table.add_row("[bold cyan]Varlık Kategorileri (Entity Breakdown)[/bold cyan]", "")
                for ent_type, count in by_ent.items():
                    overview_table.add_row(f"  • {ent_type.upper()}", str(count))

            # Top Tags
            top_tags = stats.get("top_tags", {})
            if top_tags:
                overview_table.add_section()
                tags_str = " | ".join(f"[blue]{tag}[/blue] ({cnt})" for tag, cnt in list(top_tags.items())[:8])
                overview_table.add_row("[bold cyan]Öne Çıkan Etiketler (Top Tags)[/bold cyan]", tags_str)

            console.print(overview_table)

            # 2. Key Findings Table
            top_findings = stats.get("top_findings", [])
            if top_findings:
                console.print()
                f_table = Table(title=f"🔎 Önemli İstihbarat Bulguları (Top Findings: {target_name})", border_style="green")
                f_table.add_column("Kategori (Entity)", style="bold cyan")
                f_table.add_column("Bulgu Başlığı (Title)", style="bold yellow")
                f_table.add_column("Sağlayıcı (Provider)", style="blue")
                f_table.add_column("Güven (Confidence)", justify="right", style="magenta")
                f_table.add_column("Not Dosyası (Vault Path)", style="dim")

                for f in top_findings:
                    conf_pct = f"{f['confidence_score'] * 100:.1f}%"
                    f_table.add_row(
                        f["entity_type"].upper(),
                        f["title"],
                        f["provider_used"],
                        conf_pct,
                        f["relative_path"],
                    )
                console.print(f_table)

            # 3. Master Reports Table
            master_reports = stats.get("master_reports", [])
            if master_reports:
                console.print()
                r_table = Table(title=f"📄 Oluşturulan Ana İstihbarat Raporları (Master Reports)", border_style="yellow")
                r_table.add_column("Rapor Başlığı (Title)", style="bold yellow")
                r_table.add_column("Kasa Yolu (Vault Path)", style="green")
                r_table.add_column("Oluşturulma Tarihi (Discovered At)", justify="center", style="dim")

                for r in master_reports:
                    r_table.add_row(
                        r["title"],
                        r["relative_path"],
                        _format_ts(r.get("discovered_at"), "Unknown"),
                    )
                console.print(r_table)

        else:
            console.print(f"[bold red]Bilinmeyen alt işlem: '{action}'. Desteklenenler: create, switch, current, list, delete, info.[/bold red]")

