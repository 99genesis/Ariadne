"""Instagram social network username intelligence provider."""

import re
from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class InstagramProvider(BaseUsernameProvider):
    """Checks Instagram profile using public HTML/Meta extraction and status fallback."""

    @property
    def provider_name(self) -> str:
        return "Instagram"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://www.instagram.com/{username}/"

    async def _extract_from_html(
        self, session: aiohttp.ClientSession, username: str, html_content: str, status_code: int
    ) -> Optional[BaseUsernameProfile]:
        og_title = self._extract_meta_content(html_content, "og:title")
        og_desc = self._extract_meta_content(html_content, "og:description")
        og_image = self._extract_meta_content(html_content, "og:image")

        followers = None
        following = None
        posts = None

        if og_desc:
            m_f = re.search(r"([\d,.\w]+)\s+Followers?,\s+([\d,.\w]+)\s+Following?,\s+([\d,.\w]+)\s+Posts?", og_desc, re.IGNORECASE)
            if m_f:
                try:
                    followers = int(re.sub(r"[^\d]", "", m_f.group(1)))
                    following = int(re.sub(r"[^\d]", "", m_f.group(2)))
                    posts = int(re.sub(r"[^\d]", "", m_f.group(3)))
                except Exception:
                    pass

        display_name = og_title
        if og_title and ("•" in og_title or "(" in og_title):
            display_name = og_title.split("•")[0].split("(")[0].strip()

        if og_title or og_desc or og_image:
            return SocialProfile(
                username=username,
                display_name=display_name or username,
                profile_url=f"https://www.instagram.com/{username}/",
                is_present=True,
                avatar_url=og_image,
                bio=og_desc,
                status_code=status_code,
                confidence_score=0.92,
                category=self.category,
                platform_name=self.provider_name,
                followers_count=followers,
                following_count=following,
                posts_count=posts,
                raw_metadata={"og_title": og_title, "og_description": og_desc},
            )
        return None
