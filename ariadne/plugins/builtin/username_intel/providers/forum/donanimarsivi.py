"""Donanim Arsivi Forum community username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, ForumProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class DonanimArsiviProvider(BaseUsernameProvider):
    """Checks Donanim Arsivi Forum community."""

    @property
    def provider_name(self) -> str:
        return "DonanimArsivi"

    @property
    def category(self) -> str:
        return "forum"

    @property
    def url_template(self) -> str:
        return "https://forum.donanimarsivi.com/ara/?q={username}&t=post&o=relevance"

    async def _extract_from_html(
        self, session: aiohttp.ClientSession, username: str, html_content: str, status_code: int
    ) -> Optional[BaseUsernameProfile]:
        if self._is_false_positive(html_content):
            return None

        lower_html = html_content.lower()
        empty_indicators = [
            "hiçbir sonuç bulunamadı",
            "sonuç bulunamadı",
            "eşleşen hiçbir konu veya mesaj bulunamadı",
            "arama kriterlerinize uygun",
            "no results found",
            "konularda ara",
            'data-template="search_form"',
        ]
        if any(ind in lower_html for ind in empty_indicators):
            return None

        og_title = self._extract_meta_content(html_content, "og:title") or self._extract_title(html_content)
        display_name = og_title.split("|")[0].strip() if og_title else f"{username} (DonanimArsivi Forum)"
        return ForumProfile(
            username=username,
            display_name=display_name,
            profile_url=self.url_template.format(username=username),
            is_present=True,
            status_code=status_code,
            confidence_score=0.88,
            category=self.category,
            platform_name=self.provider_name,
            raw_metadata={"og_title": og_title},
        )
