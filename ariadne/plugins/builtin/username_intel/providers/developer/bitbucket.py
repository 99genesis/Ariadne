"""Bitbucket username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class BitbucketProvider(BaseUsernameProvider):
    """Checks Bitbucket profile using public endpoint and HTML/API."""

    @property
    def provider_name(self) -> str:
        return "Bitbucket"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://bitbucket.org/{username}/"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://api.bitbucket.org/2.0/users/{username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    avatar = data.get("links", {}).get("avatar", {}).get("href")
                    return DeveloperProfile(
                        username=username,
                        display_name=data.get("display_name") or username,
                        profile_url=f"https://bitbucket.org/{username}/",
                        is_present=True,
                        avatar_url=avatar,
                        created_at=data.get("created_on"),
                        status_code=200,
                        confidence_score=0.97,
                        category=self.category,
                        platform_name=self.provider_name,
                        raw_metadata=data,
                    )
        except Exception:
            pass
        return None
