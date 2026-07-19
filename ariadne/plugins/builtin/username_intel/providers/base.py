"""Abstract Base Class and Protocol for all Username Intelligence Providers.

Implements the 3-Tier Layered Intelligence Gathering Strategy:
- Tier 1: Public JSON API / oEmbed endpoint query.
- Tier 2: Public HTML & OpenGraph / Meta / JSON-LD tag extraction.
- Tier 3: HTTP Status Code verification fallback (200 OK / 404 Not Found).
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile
from ariadne.plugins.builtin.username_intel.rate_limiter import RateLimiter


@runtime_checkable
class IUsernameProvider(Protocol):
    """Protocol contract for all username intelligence providers."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def category(self) -> str:
        ...

    @property
    def url_template(self) -> str:
        ...

    async def check_profile(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        ...


class BaseUsernameProvider(ABC, IUsernameProvider):
    """Abstract implementation providing rate-limited 3-Tier Layered OSINT analysis."""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None) -> None:
        self.rate_limiter = rate_limiter or RateLimiter(host=self.provider_name)

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Friendly platform name e.g. GitHub."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Category e.g. developer, social, gaming, forum."""
        pass

    @property
    @abstractmethod
    def url_template(self) -> str:
        """Profile URL pattern e.g. https://github.com/{username}."""
        pass

    async def _check_api(
        self, session: aiohttp.ClientSession, username: str
    ) -> Optional[BaseUsernameProfile]:
        """Tier 1: Override to check public JSON API or oEmbed. Return profile if found."""
        return None

    async def _extract_from_html(
        self, session: aiohttp.ClientSession, username: str, html_content: str, status_code: int
    ) -> Optional[BaseUsernameProfile]:
        """Tier 2: Extract metadata from public HTML (OpenGraph/JSON-LD)."""
        og_title = self._extract_meta_content(html_content, "og:title") or self._extract_title(html_content)
        og_desc = self._extract_meta_content(html_content, "og:description") or self._extract_meta_name(html_content, "description")
        og_image = self._extract_meta_content(html_content, "og:image")

        profile_url = self.url_template.format(username=username)

        # If page has valid OG profile data or title containing username
        if og_title or og_desc or og_image:
            return BaseUsernameProfile(
                username=username,
                display_name=og_title,
                profile_url=profile_url,
                is_present=True,
                avatar_url=og_image,
                bio=og_desc,
                status_code=status_code,
                confidence_score=0.88,
                category=self.category,
                platform_name=self.provider_name,
                raw_metadata={"og_title": og_title, "og_description": og_desc, "og_image": og_image},
            )
        return None

    def _extract_meta_content(self, html: str, property_name: str) -> Optional[str]:
        pattern = re.compile(
            rf'<meta\s+[^>]*property=["\']{re.escape(property_name)}["\'][^>]*content=["\']([^"\']+)["\']|'
            rf'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']{re.escape(property_name)}["\']',
            re.IGNORECASE,
        )
        m = pattern.search(html)
        if m:
            return (m.group(1) or m.group(2)).strip()
        return None

    def _extract_meta_name(self, html: str, name_attr: str) -> Optional[str]:
        pattern = re.compile(
            rf'<meta\s+[^>]*name=["\']{re.escape(name_attr)}["\'][^>]*content=["\']([^"\']+)["\']|'
            rf'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']{re.escape(name_attr)}["\']',
            re.IGNORECASE,
        )
        m = pattern.search(html)
        if m:
            return (m.group(1) or m.group(2)).strip()
        return None

    def _extract_title(self, html: str) -> Optional[str]:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return m.group(1).strip() if m else None

    async def check_profile(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        """Execute 3-Tier Layered OSINT analysis with RateLimiter and backoff."""
        clean_user = username.strip().replace("@", "")
        if not clean_user:
            return None

        async def _run_checks() -> Optional[BaseUsernameProfile]:
            # Tier 1: Check Public API if available
            api_profile = await self._check_api(session, clean_user)
            if api_profile is not None:
                return api_profile

            # Tier 2 & 3: Check HTML Page & HTTP Status
            url = self.url_template.format(username=clean_user)
            try:
                async with session.get(url, allow_redirects=True, timeout=10) as resp:
                    if resp.status == 404:
                        return None
                    if resp.status in (429, 503, 403):
                        raise ProviderRateLimitException(
                            message=f"Rate limit or challenge encountered ({resp.status}) for {self.provider_name}",
                            provider_id=self.provider_name,
                        )
                    if resp.status != 200:
                        return None

                    html = await resp.text()

                    # Check false positive signatures common on some platforms (e.g. "page not found" in body)
                    if self._is_false_positive(html):
                        return None

                    # Tier 2: HTML Extraction
                    html_profile = await self._extract_from_html(session, clean_user, html, resp.status)
                    if html_profile is not None:
                        return html_profile

                    # Tier 3: HTTP Status Code Fallback
                    return BaseUsernameProfile(
                        username=clean_user,
                        display_name=clean_user,
                        profile_url=url,
                        is_present=True,
                        status_code=resp.status,
                        confidence_score=0.80,
                        category=self.category,
                        platform_name=self.provider_name,
                        raw_metadata={"status_code": resp.status, "tier": "status_fallback"},
                    )
            except Exception:
                return None

        try:
            return await self.rate_limiter.execute_with_retry(_run_checks)
        except Exception:
            return None

    def _is_false_positive(self, html_content: str) -> bool:
        """Check known strings indicating non-existent profile despite HTTP 200."""
        lower_html = html_content.lower()
        signatures = [
            "page not found",
            "this account doesn't exist",
            "user not found",
            "kullanıcı bulunamadı",
            "böyle bir sayfa yok",
            "404 not found",
            "belirtilen profil bulunamadı",
            "the specified profile could not be found",
            "error_ctn",
            "an error occurred while processing your request",
            "işleminiz sırasında bir hata meydana geldi",
            "profile not found",
            "this user does not exist",
            "checking your browser - recaptcha",
            "client challenge",
            "attention required! | cloudflare",
            "just a moment...",
            "please wait for verification",
            "group chat that",
            "discord - group chat",
            "a new way to chat",
            "invite-invalid",
            "invite expired or invalid",
            "konularda ara",
            'data-template="search_form"',
        ]
        return any(sig in lower_html for sig in signatures)
