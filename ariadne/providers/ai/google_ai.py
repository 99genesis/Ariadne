"""Google AI Studio / Gemini API Provider implementation.

Supports dynamic list_models via google-genai SDK or REST API, validates credentials
against September 2026 standards, and provides multi-tier Vision geolocation analysis.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
import aiohttp

from ariadne.core.exceptions import ProviderAuthenticationException, ProviderException
from ariadne.core.interfaces import ILogger, ISecretsManager, ITextLLMCapable, IVisionCapable
from ariadne.core.models import ProviderModelInfo
from ariadne.providers.base_provider import BaseVisionProvider


class GoogleAIProvider(BaseVisionProvider, ITextLLMCapable, IVisionCapable):
    """Google AI Studio / Gemini provider supporting live model discovery and vision analysis."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        secrets_manager: Optional[ISecretsManager] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        super().__init__(secrets_manager=secrets_manager, logger=logger)

    @property
    def provider_id(self) -> str:
        return "google_ai"

    async def validate_credentials(self, api_key: Optional[str] = None) -> bool:
        """Validate API key by querying models list endpoint."""
        key = await self._get_api_key(explicit_key=api_key)
        if not key:
            return False

        url = f"{self.BASE_URL}/models?key={key}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return True
                    if self.logger:
                        self.logger.warning(
                            f"Google AI credential validation failed with status {resp.status}"
                        )
                    return False
            except Exception as exc:
                if self.logger:
                    self.logger.debug(f"Google AI validate_credentials network error: {exc}")
                return False

    async def list_models(self) -> List[ProviderModelInfo]:
        """Dynamically fetch available models from Google AI Studio."""
        key = await self._get_api_key()
        if not key:
            if self.logger:
                self.logger.debug("No Google AI API key configured; returning empty model list.")
            return []

        url = f"{self.BASE_URL}/models?key={key}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=15) as resp:
                    body = await resp.text()
                    if resp.status != 200:
                        self._handle_http_error(resp.status, body, url)

                    data = json.loads(body)
                    models_raw = data.get("models", [])
                    models_list: List[ProviderModelInfo] = []

                    for m in models_raw:
                        name: str = m.get("name", "")
                        clean_id = name.replace("models/", "") if name.startswith("models/") else name
                        methods: List[str] = m.get("supportedGenerationMethods", [])

                        if "generateContent" not in methods:
                            continue

                        caps = ["text"]
                        is_non_image = any(x in clean_id.lower() for x in ["tts", "audio", "robotics", "embedding", "aqa", "bison"])
                        if not is_non_image and ("vision" in clean_id.lower() or "gemini" in clean_id.lower()):
                            caps.append("vision")
                        if "pro" in clean_id.lower() or "flash" in clean_id.lower():
                            caps.append("json_mode")

                        info = ProviderModelInfo(
                            model_id=clean_id,
                            display_name=m.get("displayName", clean_id),
                            capabilities=caps,
                            context_window=m.get("inputTokenLimit", 128000),
                            is_free_tier_compatible="pro" not in clean_id.lower() or "flash" in clean_id.lower(),
                        )
                        models_list.append(info)

                    self._cached_models = models_list
                    return models_list

            except aiohttp.ClientError as exc:
                raise ProviderException(
                    message=f"Network error while listing Google AI models: {exc}",
                    provider_id=self.provider_id,
                )

    async def generate_text(
        self,
        prompt: str,
        model_id: str,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """Generate text or structured JSON from Gemini."""
        key = await self._get_api_key()
        if not key:
            raise ProviderAuthenticationException(provider_id=self.provider_id)

        url = f"{self.BASE_URL}/models/{model_id}:generateContent?key={key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=45) as resp:
                body = await resp.text()
                if resp.status != 200:
                    self._handle_http_error(resp.status, body, url)

                data = json.loads(body)
                try:
                    candidates = data.get("candidates", [])
                    if not candidates:
                        return ""
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return str(parts[0].get("text", "")) if parts else ""
                except Exception as exc:
                    raise ProviderException(
                        message=f"Failed to parse Google AI generateContent response: {exc}",
                        provider_id=self.provider_id,
                    )

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        model_id: str,
        hint_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze image bytes with multi-tier Geo-INT structured JSON output."""
        key = await self._get_api_key()
        if not key:
            raise ProviderAuthenticationException(provider_id=self.provider_id)

        import base64
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        geo_prompt = prompt
        if hint_location:
            geo_prompt += f"\n\n[HINT LOCATION PROVIDED BY TARGET METADATA]: {hint_location}. Use this hint to refine your specific city/region/country estimates."

        system_prompt = (
            "You are an elite OSINT Geo-Intelligence imagery analyst. Examine the architectural "
            "style, vegetation, signage, license plates, shop names, street layout, power lines, and lighting in the image. "
            "Provide a 4-tier hierarchical location prediction in exact JSON format with the following keys:\n"
            "{\n"
            '  "district_guess": "Specific district, neighborhood, borough, or ilçe/semt guess (e.g. Kadıköy, Beşiktaş, Manhattan)",\n'
            '  "city_guess": "Specific city or High Probability guess",\n'
            '  "region_guess": "Regional/Province or Medium Probability guess",\n'
            '  "country_guess": "Country level or Low Probability guess",\n'
            '  "confidence": 0.85,\n'
            '  "reasoning": "Brief technical breakdown of visual indicators observed"\n'
            "}"
        )

        url = f"{self.BASE_URL}/models/{model_id}:generateContent?key={key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "parts": [
                        {"text": geo_prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": b64_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"responseMimeType": "application/json"},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=60) as resp:
                body = await resp.text()
                if resp.status != 200:
                    self._handle_http_error(resp.status, body, url)

                data = json.loads(body)
                try:
                    candidates = data.get("candidates", [])
                    if not candidates:
                        return {}
                    parts = candidates[0].get("content", {}).get("parts", [])
                    raw_text = parts[0].get("text", "{}") if parts else "{}"
                    result_dict: Dict[str, Any] = json.loads(raw_text)
                    return result_dict
                except Exception as exc:
                    if self.logger:
                        self.logger.warning(f"Failed to parse Google AI JSON response: {exc}")
                    return {
                        "district_guess": "Unknown",
                        "city_guess": "Unknown",
                        "region_guess": "Unknown",
                        "country_guess": "Unknown",
                        "confidence": 0.0,
                        "reasoning": f"JSON parse error: {exc}",
                    }
