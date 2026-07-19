"""Twitter / X social network username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class TwitterProvider(BaseUsernameProvider):
    """Checks Twitter / X profile using Syndication/HTML and oEmbed."""

    @property
    def provider_name(self) -> str:
        return "Twitter"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://x.com/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        # Try syndication user details
        api_url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    if f'screen_name":"{username.lower()}"' in html.lower() or f"@{username}" in html:
                        return SocialProfile(
                            username=username,
                            display_name=username,
                            profile_url=f"https://x.com/{username}",
                            is_present=True,
                            status_code=200,
                            confidence_score=0.95,
                            category=self.category,
                            platform_name=self.provider_name,
                        )
        except Exception:
            pass
        return None
