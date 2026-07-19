"""OpenRouter & Ollama providers for multi-cloud fallback and local/offline execution."""

import base64
import json
from typing import Any, Dict, List, Optional
import aiohttp

from ariadne.core.exceptions import ProviderException, ProviderAuthenticationException
from ariadne.core.interfaces import ILogger, ISecretsManager, ITextLLMCapable, IVisionCapable
from ariadne.core.models import ProviderModelInfo
from ariadne.providers.base_provider import BaseAIProvider, BaseVisionProvider


class OpenRouterProvider(BaseVisionProvider, ITextLLMCapable, IVisionCapable):
    """OpenRouter multi-cloud aggregator provider supporting 200+ models including multi-modal vision."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self, secrets_manager: Optional[ISecretsManager] = None, logger: Optional[ILogger] = None
    ) -> None:
        super().__init__(secrets_manager=secrets_manager, logger=logger)

    @property
    def provider_id(self) -> str:
        return "openrouter"

    async def validate_credentials(self, api_key: Optional[str] = None) -> bool:
        key = await self._get_api_key(explicit_key=api_key)
        if not key:
            return False
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.BASE_URL}/models", timeout=10) as resp:
                    return resp.status == 200
            except Exception:
                return False

    async def list_models(self) -> List[ProviderModelInfo]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.BASE_URL}/models", timeout=15) as resp:
                    body = await resp.text()
                    if resp.status != 200:
                        return []
                    data = json.loads(body)
                    models_list: List[ProviderModelInfo] = []
                    for m in data.get("data", []):
                        mid = m.get("id", "")
                        caps = ["text"]
                        if any(kw in mid.lower() for kw in ["vision", "gpt-4o", "gemini", "claude-3", "pixtral", "llava"]):
                            caps.append("vision")
                        models_list.append(
                            ProviderModelInfo(
                                model_id=mid,
                                display_name=m.get("name", mid),
                                capabilities=caps,
                                context_window=m.get("context_length", 32768),
                            )
                        )
                    return models_list
            except Exception as exc:
                if self.logger:
                    self.logger.warning(f"OpenRouter list_models failed: {exc}")
                return []

    async def generate_text(
        self, prompt: str, model_id: str, system_instruction: Optional[str] = None, json_mode: bool = False
    ) -> str:
        key = await self._get_api_key()
        headers = {"Authorization": f"Bearer {key or ''}", "Content-Type": "application/json"}
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model_id, "messages": messages}
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


class OllamaProvider(BaseAIProvider, ITextLLMCapable):
    """Local offline Ollama provider supporting GGUF local models."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        secrets_manager: Optional[ISecretsManager] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        super().__init__(secrets_manager=secrets_manager, logger=logger)
        self.base_url = base_url.rstrip("/")

    @property
    def provider_id(self) -> str:
        return "ollama"

    async def validate_credentials(self, api_key: Optional[str] = None) -> bool:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/api/tags", timeout=5) as resp:
                    return resp.status == 200
            except Exception:
                return False

    async def list_models(self) -> List[ProviderModelInfo]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/api/tags", timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    models_list: List[ProviderModelInfo] = []
                    for m in data.get("models", []):
                        name = m.get("name", "")
                        caps = ["text"]
                        if "llava" in name.lower() or "molmo" in name.lower():
                            caps.append("vision")
                        models_list.append(
                            ProviderModelInfo(
                                model_id=name,
                                display_name=f"Ollama Local ({name})",
                                capabilities=caps,
                                context_window=8192,
                            )
                        )
                    return models_list
            except Exception as exc:
                if self.logger:
                    self.logger.debug(f"Ollama list_models offline: {exc}")
                return []

    async def generate_text(
        self, prompt: str, model_id: str, system_instruction: Optional[str] = None, json_mode: bool = False
    ) -> str:
        payload: Dict[str, Any] = {"model": model_id, "prompt": prompt, "stream": False}
        if system_instruction:
            payload["system"] = system_instruction
        if json_mode:
            payload["format"] = "json"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.base_url}/api/generate", json=payload, timeout=60) as resp:
                    if resp.status != 200:
                        self._handle_http_error(resp.status, await resp.text(), f"{self.base_url}/api/generate")
                    data = await resp.json()
                    return str(data.get("response", ""))
            except Exception as exc:
                raise ProviderException(message=f"Ollama request error: {exc}", provider_id=self.provider_id)
