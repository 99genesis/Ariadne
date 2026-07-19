"""OpenAI / Vision Provider implementation for Ariadne.

Supports live model discovery via https://api.openai.com/v1/models and Vision analysis.
"""

import base64
import json
from typing import Any, Dict, List, Optional
import aiohttp

from ariadne.core.exceptions import ProviderAuthenticationException, ProviderException
from ariadne.core.interfaces import ILogger, ISecretsManager, ITextLLMCapable, IVisionCapable
from ariadne.core.models import ProviderModelInfo
from ariadne.providers.base_provider import BaseVisionProvider


class OpenAIProvider(BaseVisionProvider, ITextLLMCapable, IVisionCapable):
    """OpenAI API provider supporting GPT-4o, dynamic listing, and Vision capabilities."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(
        self,
        secrets_manager: Optional[ISecretsManager] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        super().__init__(secrets_manager=secrets_manager, logger=logger)

    @property
    def provider_id(self) -> str:
        return "openai"

    async def validate_credentials(self, api_key: Optional[str] = None) -> bool:
        key = await self._get_api_key(explicit_key=api_key)
        if not key:
            return False

        headers = {"Authorization": f"Bearer {key}"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.BASE_URL}/models", headers=headers, timeout=10) as resp:
                    return resp.status == 200
            except Exception:
                return False

    async def list_models(self) -> List[ProviderModelInfo]:
        key = await self._get_api_key()
        if not key:
            return []

        headers = {"Authorization": f"Bearer {key}"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.BASE_URL}/models", headers=headers, timeout=15) as resp:
                    body = await resp.text()
                    if resp.status != 200:
                        self._handle_http_error(resp.status, body, f"{self.BASE_URL}/models")

                    data = json.loads(body)
                    models_raw = data.get("data", [])
                    models_list: List[ProviderModelInfo] = []

                    for m in models_raw:
                        mid = m.get("id", "")
                        if not ("gpt-4" in mid or "gpt-3.5" in mid or "o1" in mid or "o3" in mid):
                            continue

                        caps = ["text"]
                        if "gpt-4o" in mid or "vision" in mid:
                            caps.append("vision")
                        if "gpt-4" in mid or "gpt-3.5-turbo" in mid:
                            caps.append("json_mode")

                        models_list.append(
                            ProviderModelInfo(
                                model_id=mid,
                                display_name=f"OpenAI {mid}",
                                capabilities=caps,
                                context_window=128000 if "gpt-4" in mid else 16384,
                            )
                        )
                    return models_list
            except Exception as exc:
                raise ProviderException(
                    message=f"Failed to list OpenAI models: {exc}", provider_id=self.provider_id
                )

    async def generate_text(
        self,
        prompt: str,
        model_id: str,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        key = await self._get_api_key()
        if not key:
            raise ProviderAuthenticationException(provider_id=self.provider_id)

        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        messages: List[Dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {"model": model_id, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.BASE_URL}/chat/completions", headers=headers, json=payload, timeout=45) as resp:
                body = await resp.text()
                if resp.status != 200:
                    self._handle_http_error(resp.status, body, f"{self.BASE_URL}/chat/completions")
                data = json.loads(body)
                choices = data.get("choices", [])
                return str(choices[0]["message"]["content"]) if choices else ""

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        model_id: str,
        hint_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        key = await self._get_api_key()
        if not key:
            raise ProviderAuthenticationException(provider_id=self.provider_id)

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

        full_prompt = prompt
        if hint_location:
            full_prompt += f"\n\n[LOCATION HINT]: {hint_location}"
        full_prompt += (
            "\nRespond strictly in JSON format with keys: "
            "district_guess (specific district/neighborhood/borough/ilçe), city_guess, region_guess, country_guess, confidence (0.0-1.0), reasoning."
        )

        payload = {
            "model": model_id,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                    ],
                }
            ],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60) as resp:
                body = await resp.text()
                if resp.status != 200:
                    self._handle_http_error(resp.status, body, f"{self.BASE_URL}/chat/completions")
                data = json.loads(body)
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                try:
                    return dict(json.loads(content))
                except Exception:
                    return {"district_guess": "Unknown", "city_guess": "Unknown", "region_guess": "Unknown", "country_guess": "Unknown", "confidence": 0.0, "reasoning": "Failed to parse JSON"}
