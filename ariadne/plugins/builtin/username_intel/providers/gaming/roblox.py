"""Roblox gaming platform username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, GamingProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class RobloxProvider(BaseUsernameProvider):
    """Checks Roblox username using public Users REST API."""

    @property
    def provider_name(self) -> str:
        return "Roblox"

    @property
    def category(self) -> str:
        return "gaming"

    @property
    def url_template(self) -> str:
        return "https://www.roblox.com/users/profile?username={username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    data_list = data.get("data", [])
                    for item in data_list:
                        if item.get("name", "").strip().lower() == username.strip().lower():
                            user_id = item.get("id")
                            return GamingProfile(
                                username=username,
                                display_name=item.get("displayName") or username,
                                profile_url=f"https://www.roblox.com/users/{user_id}/profile",
                                is_present=True,
                                status_code=200,
                                confidence_score=0.98,
                                category=self.category,
                                platform_name=self.provider_name,
                                is_verified=item.get("hasVerifiedBadge", False),
                                raw_metadata=item,
                            )
        except Exception:
            pass
        return None
