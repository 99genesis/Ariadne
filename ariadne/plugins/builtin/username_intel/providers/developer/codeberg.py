"""Codeberg username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class CodebergProvider(BaseUsernameProvider):
    """Checks Codeberg profile using API and HTML fallback."""

    @property
    def provider_name(self) -> str:
        return "Codeberg"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://codeberg.org/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://codeberg.org/api/v1/users/{username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return DeveloperProfile(
                        username=username,
                        display_name=data.get("full_name") or data.get("login") or username,
                        profile_url=f"https://codeberg.org/{username}",
                        is_present=True,
                        avatar_url=data.get("avatar_url"),
                        bio=data.get("description"),
                        created_at=data.get("created"),
                        status_code=200,
                        confidence_score=0.98,
                        category=self.category,
                        platform_name=self.provider_name,
                        raw_metadata=data,
                    )
        except Exception:
            pass
        return None
