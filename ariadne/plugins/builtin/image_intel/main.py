"""Image & Vision GEO-INT Plugin implementing IPlugin."""

from pathlib import Path
from typing import Any, Dict, List
import aiofiles

from ariadne.core.interfaces import IEventBus, IPlugin, IProvider, IVisionCapable
from ariadne.core.models import IntelligenceResult, TargetEntity, TargetType
from ariadne.events.topics import ImageGeoResolvedEvent


class ImageIntelPlugin(IPlugin):
    """Performs multi-tier GEO-INT and EXIF analysis on target images."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.event_bus: IEventBus | None = None

    @property
    def plugin_id(self) -> str:
        return "ariadne.builtin.image_intel"

    async def initialize(self, config: Dict[str, Any], event_bus: IEventBus) -> bool:
        self.config = config
        self.event_bus = event_bus
        return True

    async def can_handle(self, target: TargetEntity) -> bool:
        return target.target_type == TargetType.IMAGE or "image_path" in target.metadata

    async def execute(self, target: TargetEntity, providers: Dict[str, IProvider]) -> List[IntelligenceResult]:
        try:
            image_path_str = target.metadata.get("image_path", target.display_name)
            img_path = Path(image_path_str)
            if not img_path.exists():
                return []

            async with aiofiles.open(img_path, "rb") as f:
                img_bytes = await f.read()

            # 1. Hash Calculation
            import hashlib
            import io
            from PIL import Image, ExifTags

            file_sha256 = hashlib.sha256(img_bytes).hexdigest()
            file_md5 = hashlib.md5(img_bytes).hexdigest()

            # 2. Image Metadata & EXIF Extraction
            exif_data: Dict[str, Any] = {}
            gps_coords: Optional[Dict[str, float]] = None
            width, height = 0, 0
            img_format = "UNKNOWN"

            try:
                with Image.open(io.BytesIO(img_bytes)) as pil_img:
                    width, height = pil_img.size
                    img_format = pil_img.format or "UNKNOWN"

                    raw_exif = pil_img.getexif()
                    if raw_exif:
                        for tag_id, value in raw_exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            if isinstance(value, (bytes, bytearray)):
                                continue
                            if tag_name == "GPSInfo" and isinstance(value, dict):
                                gps_raw = {}
                                for key, val in value.items():
                                    sub_tag = ExifTags.GPSTAGS.get(key, str(key))
                                    if not isinstance(val, (bytes, bytearray)):
                                        gps_raw[sub_tag] = str(val)
                                exif_data["GPSInfo"] = gps_raw
                                try:
                                    def _to_float(v: Any) -> float:
                                        if hasattr(v, "numerator") and hasattr(v, "denominator"):
                                            return float(v.numerator) / float(v.denominator)
                                        return float(v)
                                    if 2 in value and 4 in value:
                                        lat_deg = _to_float(value[2][0]) + _to_float(value[2][1])/60.0 + _to_float(value[2][2])/3600.0
                                        if value.get(1) == "S":
                                            lat_deg = -lat_deg
                                        lon_deg = _to_float(value[4][0]) + _to_float(value[4][1])/60.0 + _to_float(value[4][2])/3600.0
                                        if value.get(3) == "W":
                                            lon_deg = -lon_deg
                                        gps_coords = {"lat": lat_deg, "lon": lon_deg}
                                except Exception:
                                    pass
                            else:
                                exif_data[tag_name] = str(value)
            except Exception:
                pass

            # 3. OCR / File Info fallback extraction
            ocr_text = ""
            try:
                import pytesseract
                with Image.open(io.BytesIO(img_bytes)) as pil_img:
                    ocr_text = pytesseract.image_to_string(pil_img).strip()
            except Exception:
                ocr_text = "OCR engine not available / No text detected"

            results = []
            ocr_status = ocr_text[:100] + "..." if len(ocr_text) > 100 else ocr_text

            # 4. EXIF & Metadata Result Construction (unless ai_only requested)
            if target.metadata.get("ai_only") != "true":
                exif_links = []
                exif_entity = "image_analysis"
                if gps_coords:
                    exif_entity = "location"
                    exif_links.append(f"[[Location_{gps_coords['lat']:.4f}_{gps_coords['lon']:.4f}]]")

                exif_result = IntelligenceResult(
                    title=f"Görsel İstihbarat & EXIF Analizi: {img_path.name}",
                    entity_type=exif_entity,
                    source_plugin=self.plugin_id,
                    provider_used="exif_hash_fallback",
                    confidence_score=1.0 if gps_coords else 0.85,
                    tags=["#osint/image", "#exif/metadata", "#technical"],
                    links_to=exif_links,
                    metadata={
                        "image_file": str(img_path),
                        "sha256": file_sha256,
                        "md5": file_md5,
                        "dimensions": f"{width}x{height}",
                        "format": img_format,
                        "exif": exif_data,
                        "gps": gps_coords or {},
                        "ocr_text": ocr_text,
                    },
                    content_markdown=f"### 📷 Görsel Teknik Rapor (EXIF & Metadata)\n- **Dosya:** `{img_path.name}`\n- **Boyutlar:** `{width}x{height}` (`{img_format}`)\n- **SHA-256 Hash:** `{file_sha256}`\n- **MD5 Hash:** `{file_md5}`\n- **EXIF Bilgisi:** `{len(exif_data)} etiket çıkarıldı`\n- **GPS Koordinatları:** `{gps_coords if gps_coords else 'Tespit edilemedi'}`\n\n#### 📑 OCR / Metin Taraması\n```\n{ocr_text}\n```\n",
                )
                results.append(exif_result)

            # 5. AI Vision GEO-INT Analysis (unless exif_only requested)
            if target.metadata.get("exif_only") != "true":
                vision_provider: IVisionCapable | None = None
                provider_manager = None
                try:
                    from ariadne.core.container import container
                    from ariadne.providers.provider_manager import ProviderManager
                    provider_manager = container.resolve(ProviderManager)
                    vision_provider = provider_manager.get_active_vision_provider()
                except Exception:
                    pass

                if not vision_provider:
                    for provider in providers.values():
                        if isinstance(provider, IVisionCapable):
                            vision_provider = provider
                            break

                if vision_provider and provider_manager:
                    try:
                        hint = target.metadata.get("hint_location")

                        analysis = await provider_manager.analyze_vision_with_fallback(
                            provider=vision_provider,
                            image_bytes=img_bytes,
                            prompt="Analyze this image for geolocation clues (architecture, foliage, signage, street names, shop signs, urban density). Return JSON with district_guess (specific district/neighborhood/ilçe/semt), city_guess, region_guess, country_guess, confidence, and reasoning.",
                            hint_location=hint,
                        )

                        district = str(analysis.get("district_guess") or analysis.get("neighborhood_guess", "Unknown"))
                        city = str(analysis.get("city_guess", "Unknown"))
                        region = str(analysis.get("region_guess", "Unknown"))
                        country = str(analysis.get("country_guess", "Unknown"))
                        conf = float(analysis.get("confidence", 0.75))
                        reasoning = str(analysis.get("reasoning", "No detailed reasoning returned."))

                        if self.event_bus:
                            await self.event_bus.publish(
                                ImageGeoResolvedEvent(
                                    target_id=target.target_id,
                                    image_path=str(img_path),
                                    district_guess=district,
                                    city_guess=city,
                                    region_guess=region,
                                    country_guess=country,
                                    confidence=conf,
                                    provider_used=vision_provider.provider_id,
                                )
                            )

                        clean_city_link = city.replace(" ", "_")
                        links = [f"[[Location_{clean_city_link}]]", f"[[Country_{country}]]"]
                        if district and district != "Unknown":
                            clean_district = district.replace(" ", "_")
                            links.insert(0, f"[[Location_{clean_district}]]")
                        if gps_coords:
                            links.append(f"[[Location_{gps_coords['lat']:.4f}_{gps_coords['lon']:.4f}]]")

                        vision_result = IntelligenceResult(
                            title=f"AI Görsel GEO-INT Analizi: {img_path.name}",
                            entity_type="location",
                            source_plugin=self.plugin_id,
                            provider_used=vision_provider.provider_id,
                            confidence_score=conf,
                            tags=["#osint/geoint", "#vision/ai", f"#country/{country.lower()}"],
                            links_to=links,
                            metadata={
                                "district_guess": district,
                                "city_guess": city,
                                "region_guess": region,
                                "country_guess": country,
                                "confidence": conf,
                                "image_file": str(img_path),
                                "sha256": file_sha256,
                                "reasoning": reasoning,
                            },
                            content_markdown=f"### 🌍 Multi-Tier GEO-INT Prediction (AI Vision)\n- **Sağlayıcı / Model:** `{vision_provider.provider_id}`\n- **İlçe / Semt (District):** `{district}`\n- **Şehir / İl:** `{city}`\n- **Bölge / Eyalet:** `{region}`\n- **Ülke:** `{country}`\n- **AI Güven Skoru:** `{conf * 100:.1f}%`\n\n#### 🔬 Görsel İstihbarat Mantığı (Visual Reasoning)\n{reasoning}\n",
                        )
                        results.append(vision_result)
                    except Exception as vision_exc:
                        if target.metadata.get("ai_only") == "true":
                            # If user specifically asked for ai_only and vision failed, raise or return warning
                            pass

            return results
        except Exception:
            return []

    async def cleanup(self) -> None:
        pass


def get_plugin() -> IPlugin:
    return ImageIntelPlugin()
