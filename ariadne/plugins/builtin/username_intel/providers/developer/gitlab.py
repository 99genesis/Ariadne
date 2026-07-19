"""GitLab username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class GitLabProvider(BaseUsernameProvider):
    """Checks GitLab using REST API and HTML fallback."""

    @property
    def provider_name(self) -> str:
        return "GitLab"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://gitlab.com/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://gitlab.com/api/v4/users?username={username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        user = data[0]
                        return DeveloperProfile(
                            username=username,
                            display_name=user.get("name") or username,
                            profile_url=user.get("web_url") or f"https://gitlab.com/{username}",
                            is_present=True,
                            avatar_url=user.get("avatar_url"),
                            bio=user.get("bio"),
                            created_at=user.get("created_at"),
                            status_code=200,
                            confidence_score=0.98,
                            category=self.category,
                            platform_name=self.provider_name,
                            raw_metadata=user,
                        )
        except Exception:
            pass
        return None
