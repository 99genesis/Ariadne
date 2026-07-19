"""Obsidian Exporter and Vault structure initializer.

Initializes the required .obsidian/ hidden directory, default graph view color filters,
and custom dark cyber CSS theme inside any newly created investigation vault.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
import aiofiles

from ariadne.core.exceptions import StorageException
from ariadne.core.interfaces import ILogger


class ObsidianExporter:
    """Configures Obsidian vault metadata and Graph View preferences."""

    DEFAULT_GRAPH_CONFIG: Dict[str, Any] = {
        "collapse-filter": False,
        "search": "",
        "showTags": True,
        "showAttachments": False,
        "hideUnresolved": False,
        "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": [
            {"query": "tag:#target/person", "color": {"a": 1, "rgb": 16711680}},
            {"query": "tag:#entity/social_profile", "color": {"a": 1, "rgb": 54271}},
            {"query": "tag:#entity/location", "color": {"a": 1, "rgb": 16766720}},
            {"query": "tag:#entity/phone", "color": {"a": 1, "rgb": 65280}},
            {"query": "tag:#entity/ip", "color": {"a": 1, "rgb": 1048575}},
            {"query": "tag:#entity/data_leak", "color": {"a": 1, "rgb": 16711935}},
        ],
        "collapse-display": False,
        "showArrow": True,
        "textFadeMultiplier": 0,
        "nodeSizeMultiplier": 1.2,
        "lineSizeMultiplier": 1.0,
        "collapse-forces": False,
        "centerStrength": 0.51,
        "repelStrength": 10.0,
        "linkStrength": 1.0,
        "linkDistance": 250,
        "scale": 1.0,
    }

    DEFAULT_APPEARANCE_CONFIG: Dict[str, Any] = {
        "theme": "obsidian",
        "cssTheme": "dark_cyber",
        "baseFontSize": 16,
    }

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        self.logger = logger

    async def initialize_vault(self, vault_path: Path, vault_name: str) -> bool:
        """Initialize folder structure and .obsidian config inside target vault directory."""
        try:
            vault_path.mkdir(parents=True, exist_ok=True)
            obsidian_dir = vault_path / ".obsidian"
            obsidian_dir.mkdir(parents=True, exist_ok=True)

            # Subdirectories
            for sub in ["Sosyal_Medya", "Lokasyonlar", "İletişim", "Ağ_ve_IP", "Sızıntılar", "Medya_Analiz", "Genel_Notlar"]:
                (vault_path / sub).mkdir(exist_ok=True)

            # Write graph.json
            graph_file = obsidian_dir / "graph.json"
            async with aiofiles.open(graph_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.DEFAULT_GRAPH_CONFIG, indent=2))

            # Write appearance.json
            app_file = obsidian_dir / "appearance.json"
            async with aiofiles.open(app_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.DEFAULT_APPEARANCE_CONFIG, indent=2))

            # Write root index note
            index_file = vault_path / "Index.md"
            if not index_file.exists():
                index_content = (
                    f"---\n"
                    f"id: \"index-{vault_name}\"\n"
                    f"title: \"Ana Vaka Kartı: {vault_name}\"\n"
                    f"target_id: \"{vault_name}\"\n"
                    f"entity_type: \"index\"\n"
                    f"source_module: \"ariadne.core.vault\"\n"
                    f"confidence_score: 1.0\n"
                    f"tags: [\"#index/root\", \"#status/active\"]\n"
                    f"---\n\n"
                    f"# 🎯 Operasyon Kasası: {vault_name}\n\n"
                    f"Bu klasör bir **Obsidian Kasası** olarak yapılandırılmıştır. "
                    f"Sol üst menüden **Grafik Görünümü (Graph View)** açarak tüm bağlantıları görselleştirebilirsiniz.\n\n"
                    f"## 🗂 İstihbarat Kategorileri\n"
                    f"- [[Sosyal_Medya/]] — Doğrulanan kullanıcı adları ve forum profilleri\n"
                    f"- [[Lokasyonlar/]] — Kademeli GEO-INT ve görsel analiz tahminleri\n"
                    f"- [[İletişim/]] — Telefon ve e-posta doğrulama sonuçları\n"
                    f"- [[Ağ_ve_IP/]] — IP, ASN ve Coğrafi Konum meta verileri\n"
                )
                async with aiofiles.open(index_file, "w", encoding="utf-8") as f:
                    await f.write(index_content)

            if self.logger:
                self.logger.info(f"Initialized Obsidian vault structure at {vault_path}")
            return True
        except Exception as exc:
            raise StorageException(
                message=f"Failed to initialize Obsidian vault at {vault_path}: {exc}",
                details={"error": str(exc)},
            )
