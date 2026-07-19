"""Kick live streaming username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class KickProvider(BaseUsernameProvider):
    """Checks Kick channel profile using API and HTML."""

    @property
    def provider_name(self) -> str:
        return "Kick"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://kick.com/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://kick.com/api/v1/channels/{username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user = data.get("user", {})
                    return SocialProfile(
                        username=username,
                        display_name=user.get("username") or username,
                        profile_url=f"https://kick.com/{username}",
                        is_present=True,
                        avatar_url=user.get("profile_pic"),
                        bio=user.get("bio"),
                        status_code=200,
                        confidence_score=0.98,
                        category=self.category,
                        platform_name=self.provider_name,
                        followers_count=data.get("followers_count"),
                        raw_metadata=data,
                    )
        except Exception:
            pass
        return None
