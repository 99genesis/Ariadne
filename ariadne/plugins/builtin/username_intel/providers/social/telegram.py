"""Telegram username intelligence provider."""

import re
from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class TelegramProvider(BaseUsernameProvider):
    """Checks Telegram user/channel profile using t.me HTML structure."""

    @property
    def provider_name(self) -> str:
        return "Telegram"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://t.me/{username}"

    async def _extract_from_html(
        self, session: aiohttp.ClientSession, username: str, html_content: str, status_code: int
    ) -> Optional[BaseUsernameProfile]:
        # Telegram returns 200 for missing pages, but displays specific error or lacks tgme_page_title
        if "If you have <strong>Telegram</strong>, you can contact" in html_content and "tgme_page_title" not in html_content:
            return None

        og_title = self._extract_meta_content(html_content, "og:title")
        og_desc = self._extract_meta_content(html_content, "og:description")
        og_image = self._extract_meta_content(html_content, "og:image")

        m_title = re.search(r'<div class="tgme_page_title"[^>]*>([^<]+)</div>', html_content)
        display_name = m_title.group(1).strip() if m_title else (og_title or username)

        if og_title or m_title:
            return SocialProfile(
                username=username,
                display_name=display_name,
                profile_url=f"https://t.me/{username}",
                is_present=True,
                avatar_url=og_image,
                bio=og_desc,
                status_code=status_code,
                confidence_score=0.95,
                category=self.category,
                platform_name=self.provider_name,
                raw_metadata={"og_title": og_title, "og_description": og_desc},
            )
        return None
