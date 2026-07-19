"""Steam gaming platform username intelligence provider."""

import re
from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, GamingProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class SteamProvider(BaseUsernameProvider):
    """Checks Steam custom URL profile and extracts level/summary from XML or HTML."""

    @property
    def provider_name(self) -> str:
        return "Steam"

    @property
    def category(self) -> str:
        return "gaming"

    @property
    def url_template(self) -> str:
        return "https://steamcommunity.com/id/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        xml_url = f"https://steamcommunity.com/id/{username}?xml=1"
        try:
            async with session.get(xml_url, timeout=5) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if "<error>" in text or "The specified profile could not be found" in text or "Belirtilen profil bulunamadı" in text:
                        return None

                    m_name = re.search(r"<steamID>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</steamID>", text)
                    m_avatar = re.search(r"<avatarFull>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</avatarFull>", text)
                    m_summary = re.search(r"<summary>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</summary>", text)
                    m_online = re.search(r"<onlineState>(.*?)</onlineState>", text)

                    if m_name and m_name.group(1).strip():
                        display_name = m_name.group(1).strip()
                        bio = re.sub(r"<[^>]+>", "", m_summary.group(1)).strip() if m_summary else None
                        return GamingProfile(
                            username=username,
                            display_name=display_name,
                            profile_url=f"https://steamcommunity.com/id/{username}",
                            is_present=True,
                            avatar_url=m_avatar.group(1).strip() if m_avatar else None,
                            bio=bio,
                            status_code=200,
                            confidence_score=0.99,
                            category=self.category,
                            platform_name=self.provider_name,
                            is_online=(m_online.group(1).strip() != "offline") if m_online else None,
                        )
        except Exception:
            pass
        return None

    async def _extract_from_html(
        self, session: aiohttp.ClientSession, username: str, html_content: str, status_code: int
    ) -> Optional[BaseUsernameProfile]:
        if self._is_false_positive(html_content):
            return None

        og_title = self._extract_meta_content(html_content, "og:title") or self._extract_title(html_content)
        og_image = self._extract_meta_content(html_content, "og:image")
        og_desc = self._extract_meta_content(html_content, "og:description")

        if og_title and "Steam Community ::" in og_title:
            clean_title = og_title.replace("Steam Community ::", "").strip()
            return GamingProfile(
                username=username,
                display_name=clean_title or username,
                profile_url=self.url_template.format(username=username),
                is_present=True,
                avatar_url=og_image,
                bio=og_desc,
                status_code=status_code,
                confidence_score=0.95,
                category=self.category,
                platform_name=self.provider_name,
            )
        return None

    async def check_profile(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        """Execute Steam check prioritizing HTML first to bypass aggressive CDN rate-limiting on ?xml=1."""
        clean_user = username.strip().replace("@", "")
        if not clean_user:
            return None

        async def _run_checks() -> Optional[BaseUsernameProfile]:
            url = self.url_template.format(username=clean_user)
            try:
                async with session.get(url, allow_redirects=True, timeout=10) as resp:
                    if resp.status == 404:
                        return None
                    if resp.status in (429, 503, 403):
                        from ariadne.core.exceptions import ProviderRateLimitException
                        raise ProviderRateLimitException(
                            message=f"Rate limit hit ({resp.status}) for {self.provider_name} at {url}",
                            provider_id=self.provider_name,
                        )
                    if resp.status != 200:
                        return None

                    html = await resp.text()
                    if self._is_false_positive(html):
                        return None

                    html_profile = await self._extract_from_html(session, clean_user, html, resp.status)
                    if html_profile is not None:
                        # Attempt quick non-blocking XML enrich if possible without failing
                        api_profile = await self._check_api(session, clean_user)
                        return api_profile if api_profile is not None else html_profile

                    return None
            except Exception:
                return None

        try:
            return await self.rate_limiter.execute_with_retry(_run_checks)
        except Exception:
            return None
