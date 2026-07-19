"""GitHub username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class GitHubProvider(BaseUsernameProvider):
    """Checks GitHub using public REST API and HTML fallback."""

    @property
    def provider_name(self) -> str:
        return "GitHub"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://github.com/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://api.github.com/users/{username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return DeveloperProfile(
                        username=username,
                        display_name=data.get("name") or username,
                        profile_url=f"https://github.com/{username}",
                        is_present=True,
                        avatar_url=data.get("avatar_url"),
                        bio=data.get("bio"),
                        created_at=data.get("created_at"),
                        status_code=200,
                        confidence_score=0.99,
                        category=self.category,
                        platform_name=self.provider_name,
                        repositories_count=data.get("public_repos"),
                        followers_count=data.get("followers"),
                        following_count=data.get("following"),
                        raw_metadata=data,
                    )
                elif resp.status == 404:
                    return None
        except Exception:
            pass
        return None
