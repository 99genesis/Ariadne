"""Docker Hub username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class DockerHubProvider(BaseUsernameProvider):
    """Checks Docker Hub profile."""

    @property
    def provider_name(self) -> str:
        return "DockerHub"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://hub.docker.com/u/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://hub.docker.com/v2/users/{username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return DeveloperProfile(
                        username=username,
                        display_name=data.get("full_name") or username,
                        profile_url=f"https://hub.docker.com/u/{username}",
                        is_present=True,
                        avatar_url=data.get("gravatar_url"),
                        created_at=data.get("date_joined"),
                        status_code=200,
                        confidence_score=0.97,
                        category=self.category,
                        platform_name=self.provider_name,
                        raw_metadata=data,
                    )
        except Exception:
            pass
        return None
