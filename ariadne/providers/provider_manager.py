"""Provider Manager responsible for discovery, selection, and fallback chains.

Decouples core modules from specific AI engines by providing capability-driven
selection and dynamic model listing across registered providers.
"""

from typing import Any, Dict, List, Optional, Type
from ariadne.config.config_manager import ConfigManager
from ariadne.core.exceptions import ProviderException
from ariadne.core.container import DIContainer
from ariadne.core.interfaces import (
    ILogger,
    IProvider,
    ITextLLMCapable,
    IVisionCapable,
)
from ariadne.core.models import ProviderModelInfo


class ProviderManager:
    """Manages provider registration, dynamic model discovery, and fallback selection."""

    def __init__(
        self,
        config_manager: ConfigManager,
        container: DIContainer,
        logger: Optional[ILogger] = None,
    ) -> None:
        """Initialize provider manager.

        Args:
            config_manager: Config manager for active provider & fallback settings.
            container: DI Container for resolving provider instances.
            logger: Optional logger instance.
        """
        self.config_manager = config_manager
        self.container = container
        self.logger = logger
        self._providers: Dict[str, IProvider] = {}

    def register_provider(self, provider: IProvider) -> None:
        """Register a provider instance in the manager."""
        self._providers[provider.provider_id] = provider
        if self.logger:
            self.logger.debug(
                f"Registered provider: '{provider.provider_id}' (Type: {provider.provider_type})"
            )

    def get_provider(self, provider_id: str) -> Optional[IProvider]:
        """Get registered provider by ID."""
        return self._providers.get(provider_id)

    def list_registered_providers(self, provider_type: Optional[str] = None) -> List[IProvider]:
        """List all registered providers, optionally filtered by type."""
        if provider_type:
            return [p for p in self._providers.values() if p.provider_type == provider_type]
        return list(self._providers.values())

    async def list_all_models(self) -> Dict[str, List[ProviderModelInfo]]:
        """Dynamically query all registered providers for their live available models."""
        results: Dict[str, List[ProviderModelInfo]] = {}
        for pid, provider in self._providers.items():
            try:
                models = await provider.list_models()
                results[pid] = models
            except Exception as exc:
                if self.logger:
                    self.logger.warning(f"Failed to list models for provider '{pid}': {exc}")
                results[pid] = []
        return results

    def get_active_ai_provider(self) -> ITextLLMCapable:
        """Get the primary active text LLM provider or fallback if primary is not capable/available."""
        cfg = self.config_manager.config.providers
        primary_id = cfg.active_ai_provider

        primary = self._providers.get(primary_id)
        if primary and isinstance(primary, ITextLLMCapable):
            return primary

        # Try fallback chain
        for fallback_id in cfg.fallback_providers:
            fallback = self._providers.get(fallback_id)
            if fallback and isinstance(fallback, ITextLLMCapable):
                if self.logger:
                    self.logger.info(
                        f"Primary AI provider '{primary_id}' unavailable. Using fallback '{fallback_id}'."
                    )
                return fallback

        raise ProviderException(
            message=f"No active or fallback ITextLLMCapable provider found (checked {primary_id}).",
            provider_id=primary_id,
        )

    def get_active_vision_provider(self) -> IVisionCapable:
        """Get the primary active Vision capable provider or fallback."""
        cfg = self.config_manager.config.providers
        primary_id = cfg.active_ai_provider

        primary = self._providers.get(primary_id)
        if primary and isinstance(primary, IVisionCapable):
            return primary

        # Try fallback chain
        for fallback_id in cfg.fallback_providers:
            fallback = self._providers.get(fallback_id)
            if fallback and isinstance(fallback, IVisionCapable):
                if self.logger:
                    self.logger.info(
                        f"Primary vision provider '{primary_id}' unavailable. Using fallback '{fallback_id}'."
                    )
                return fallback

        raise ProviderException(
            message=f"No active or fallback IVisionCapable provider found (checked {primary_id}).",
            provider_id=primary_id,
        )

    async def analyze_vision_with_fallback(
        self,
        provider: IVisionCapable,
        image_bytes: bytes,
        prompt: str,
        hint_location: Optional[str] = None,
    ) -> str:
        """Execute vision analysis with resilient model fallback chain and cross-provider fallback."""
        from ariadne.plugins.builtin.username_intel.rate_limiter import RateLimiter
        from ariadne.core.exceptions import ProviderRateLimitException, ProviderAuthenticationException, ProviderException
        import logging

        cfg = self.config_manager.config.providers
        log = self.logger or getattr(provider, "logger", None)

        # Build list of vision capable providers starting with primary, then fallbacks
        providers_to_try: List[IVisionCapable] = [provider]
        for fb_id in cfg.fallback_providers:
            fb = self._providers.get(fb_id)
            if fb and isinstance(fb, IVisionCapable) and getattr(fb, "provider_id", "") != getattr(provider, "provider_id", ""):
                providers_to_try.append(fb)

        last_exception = None

        for current_provider in providers_to_try:
            curr_id = getattr(current_provider, "provider_id", "unknown")
            primary_model = cfg.active_vision_model
            models_to_try = [primary_model] + [m for m in cfg.fallback_models if m != primary_model]

            if curr_id == "openrouter":
                openrouter_fallbacks = [
                    "google/gemini-2.5-flash",
                    "google/gemini-2.5-pro",
                    "google/gemini-flash-1.5",
                    "openai/gpt-4o-mini",
                    "anthropic/claude-3.5-sonnet",
                ]
                if "flash" in primary_model.lower():
                    models_to_try = ["google/gemini-2.5-flash"] + [m for m in openrouter_fallbacks if m != "google/gemini-2.5-flash"]
                elif "pro" in primary_model.lower():
                    models_to_try = ["google/gemini-2.5-pro"] + [m for m in openrouter_fallbacks if m != "google/gemini-2.5-pro"]
                elif "/" not in primary_model:
                    models_to_try = openrouter_fallbacks
                else:
                    models_to_try = [primary_model] + [m for m in openrouter_fallbacks if m != primary_model]
            elif curr_id == "google_ai":
                models_to_try = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"]

            limiter = RateLimiter(host=curr_id, max_retries=2, base_backoff=2.0, logger=self.logger)
            dynamic_fetched = False
            idx = 0

            while idx < len(models_to_try):
                model_id = models_to_try[idx]
                try:
                    async def _call_provider():
                        return await current_provider.analyze_image(
                            image_bytes=image_bytes,
                            prompt=prompt,
                            model_id=model_id,
                            hint_location=hint_location
                        )

                    result = await limiter.execute_with_retry(_call_provider)
                    return result

                except ProviderAuthenticationException as exc:
                    last_exception = exc
                    if current_provider != providers_to_try[-1]:
                        print(f"\n⚠️ [bold yellow]Sağlayıcı '{curr_id}' yetkilendirme hatası/eksik anahtar, yedek sağlayıcıya geçiliyor...[/bold yellow]")
                        break
                    print(f"\n❌ [bold red]AI Yetkilendirme Hatası[/bold red]")
                    print("API key geçersiz veya tanımlanmamış. 'setup' komutu ile kontrol edin.\n")
                    raise exc
                except ProviderRateLimitException as exc:
                    last_exception = exc
                    if idx < len(models_to_try) - 1:
                        next_model = models_to_try[idx + 1]
                        if log:
                            log.warning(f"⚠️ {model_id} kotası doldu (429), {next_model} ile devam ediliyor...")
                        print(f"\n⚠️ [bold yellow]{model_id} kotası doldu, {next_model} ile devam ediliyor...[/bold yellow]\n")
                        idx += 1
                        continue
                    elif current_provider != providers_to_try[-1]:
                        print(f"\n⚠️ [bold yellow]Sağlayıcı '{curr_id}' kotası doldu, yedek sağlayıcıya geçiliyor...[/bold yellow]")
                        break
                    else:
                        print(f"\n❌ [bold red]AI sağlayıcı kotası doldu (429/402)[/bold red]")
                        print("Ücretsiz kotanız veya krediniz dolmuş olabilir — birkaç dakika sonra tekrar deneyin veya API üzerinden billing aktif edin.\n")
                        raise exc
                except ProviderException as exc:
                    last_exception = exc
                    exc_str = str(exc).lower() + " " + str(getattr(exc, "message", "")).lower()
                    status_code = getattr(exc, "status_code", 0)
                    is_fallbackable = any(k in exc_str for k in ["404", "400", "402", "429", "payment required", "insufficient", "quota", "rate limit", "not found", "no longer available", "invalid model", "unsupported", "bad request"]) or status_code in (400, 401, 402, 403, 404, 429, 500, 502, 503, 504)
                    
                    if is_fallbackable:
                        if not dynamic_fetched and hasattr(current_provider, "list_models"):
                            dynamic_fetched = True
                            try:
                                discovered = await current_provider.list_models()
                                for info in discovered:
                                    is_non_image = any(kw in info.model_id.lower() for kw in ["tts", "audio", "robotics", "embedding", "aqa", "bison"])
                                    if "vision" in info.capabilities and info.model_id not in models_to_try and not is_non_image:
                                        models_to_try.append(info.model_id)
                            except Exception as disc_exc:
                                if self.logger:
                                    self.logger.debug(f"Dynamic model fallback discovery error: {disc_exc}")
                        if idx < len(models_to_try) - 1:
                            next_model = models_to_try[idx + 1]
                            if log:
                                log.warning(f"⚠️ Model {model_id} geçersiz/kotası yetersiz (HTTP {status_code or 'error'}), {next_model} ile devam ediliyor...")
                            print(f"\n⚠️ [bold yellow]{model_id} modeline ulaşılamadı/kredi yetersiz (HTTP {status_code or 'error'}), {next_model} ile devam ediliyor...[/bold yellow]\n")
                            idx += 1
                            continue
                        elif current_provider != providers_to_try[-1]:
                            print(f"\n⚠️ [bold yellow]Sağlayıcı '{curr_id}' tüm modellerde başarısız (HTTP {status_code or 'error'}), yedek sağlayıcıya geçiliyor...[/bold yellow]")
                            break

                    if current_provider != providers_to_try[-1]:
                        print(f"\n⚠️ [bold yellow]Sağlayıcı '{curr_id}' hatası, yedek sağlayıcıya geçiliyor...[/bold yellow]")
                        break
                    print(f"\n❌ [bold red]AI Sağlayıcı Hatası[/bold red]")
                    print(f"Hata detayı: {getattr(exc, 'message', str(exc))}\n")
                    raise exc
                except Exception as exc:
                    last_exception = exc
                    if current_provider != providers_to_try[-1]:
                        print(f"\n⚠️ [bold yellow]Sağlayıcı '{curr_id}' beklenmeyen hata ({exc}), yedek sağlayıcıya geçiliyor...[/bold yellow]")
                        break
                    print(f"\n❌ [bold red]Beklenmeyen Vision AI Hatası[/bold red]")
                    print(f"Hata detayı: {exc}\n")
                    raise exc
                idx += 1

        # If all providers and models in the fallback chain exhausted
        raise last_exception or ProviderException("All vision providers and models failed in fallback chain.", provider_id=getattr(provider, "provider_id", "unknown"))
