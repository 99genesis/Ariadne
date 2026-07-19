"""Image command handler."""

import argparse
from pathlib import Path
from typing import Dict
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo
from ariadne.core.models import TargetEntity, TargetType


class ImageCommand(BaseCommand):
    """Handler for multi-tier GEO-INT and EXIF image analysis (`image ./photo.jpg`)."""

    @property
    def command_name(self) -> str:
        return "image"

    @property
    def description(self) -> str:
        return "Resim üzerinde EXIF analizi, coğrafi konum tahmini (GEOINT) ve Vision AI analizi yapar."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="IMAGE",
            purpose=self.description,
            short_usage="image <file>",
            usage_pattern='image "<dosya_yolu>" [--hint "Konum İpucu"]',
            required_params=['<dosya_yolu> : Resim dosyasının tam veya göreli yolu (örn: "C:\\Foto\\image.jpg")'],
            optional_params=[
                '--hint, -H : Vision AI modeline konum ipucu verir (örn: --hint "İstanbul")',
                "-e, --exif-only : Yalnızca EXIF, GPS ve metadata analizi yapar, AI aramasını atlar",
                "-a, --ai-only : Yalnızca AI Vision GEO-INT analizi yapar, EXIF raporunu atlar",
                "-m, --meta : Ek meta veri key=val formatında ekler",
            ],
            examples=[
                'image "C:\\Foto\\image.jpg"',
                'image "Desktop\\test.jpg" --exif-only',
                'image "C:\\Images\\target.png" --ai-only --hint "Ankara"',
            ],
            workflow=[
                "EXIF okunur (--ai-only verilmediyse)",
                "GPS varsa çıkarılır",
                "AI görüntüyü yorumlar (--exif-only verilmediyse)",
                "Bulgular ayrı ayrı veya seçime göre listelenir",
                "Kullanıcı export eder",
            ],
            notes=[
                "Varsayılan olarak EXIF/metadata ile Vision AI tahmini ayrı bulgu (result) maddeleri halinde sunulur.",
                "Eğer EXIF içerisinde koordinat bulunursa [[Location_41.00_28.97]] olarak Obsidian grafında köprülenir.",
            ],
            error_missing_arg="image komutu bir resim dosya yolu bekliyor.\nDoğru kullanım: image \"Desktop\\test.jpg\"\nDetaylı yardım: help image",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("image_path", nargs="+", help="Analiz edilecek görsel dosyasının yolu")
        parser.add_argument("--hint", "-H", help="İsteğe bağlı konum ipucu (örn: 'İstanbul')", default="")
        parser.add_argument("--exif-only", "-e", action="store_true", help="Yalnızca EXIF ve metadata analizi yapar, AI aramasını atlar")
        parser.add_argument("--ai-only", "-a", action="store_true", help="Yalnızca AI Vision GEO-INT analizi yapar, EXIF raporunu atlar")
        parser.add_argument(
            "--meta", "-m", action="append", help="Ek meta veri key=val formatında"
        )

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        path_args = args.image_path if isinstance(args.image_path, list) else [args.image_path]
        raw_path = " ".join(path_args).strip("\"'")
        image_path = Path(raw_path)
        
        if not image_path.exists() or not image_path.is_file():
            context.logger.error(f"Image not found at path: {image_path.absolute()}")
            context.logger.warning("Kullanıcı var olmayan bir dosya yolu girdi.")
            print(f"\n❌ [bold red]File not found[/bold red]")
            print(f"Path: {image_path.absolute()}")
            print(f"Öneri: Dosya yolunu kontrol edin veya tırnak işaretlerine dikkat edin.\n")
            return
            
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        if image_path.suffix.lower() not in valid_exts:
            print(f"\n❌ [bold red]Unsupported file format[/bold red]")
            print(f"Desteklenen formatlar: {', '.join(valid_exts)}")
            print(f"Sizin dosyanız: {image_path.suffix}\n")
            return

        meta_dict: Dict[str, str] = {"image_path": str(image_path.absolute())}
        if getattr(args, "hint", None) and args.hint:
            meta_dict["hint_location"] = args.hint
        if getattr(args, "exif_only", False):
            meta_dict["exif_only"] = "true"
        if getattr(args, "ai_only", False):
            meta_dict["ai_only"] = "true"
        if getattr(args, "meta", None):
            for m in args.meta:
                if "=" in m:
                    k, v = m.split("=", 1)
                    meta_dict[k.strip()] = v.strip()

        # Clean target ID from file name (use resolved Path, not raw list)
        file_name = image_path.stem or "Image_Target"
        target = TargetEntity(
            target_id=f"Image_{file_name}",
            target_type=TargetType.IMAGE,
            display_name=file_name,
            metadata=meta_dict,
        )
        await self.run_intelligence_command(target, context, command_override="image")
