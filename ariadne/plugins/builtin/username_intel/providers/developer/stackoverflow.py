"""Stack Overflow username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class StackOverflowProvider(BaseUsernameProvider):
    """Checks Stack Overflow using StackExchange API and HTML."""

    @property
    def provider_name(self) -> str:
        return "StackOverflow"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://stackoverflow.com/users/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://api.stackexchange.com/2.3/users?inname={username}&site=stackoverflow"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    for item in items:
                        if item.get("display_name", "").strip().lower() == username.strip().lower():
                            return DeveloperProfile(
                                username=username,
                                display_name=item.get("display_name"),
                                profile_url=item.get("link") or f"https://stackoverflow.com/users/{item.get('user_id')}",
                                is_present=True,
                                avatar_url=item.get("profile_image"),
                                status_code=200,
                                confidence_score=0.97,
                                category=self.category,
                                platform_name=self.provider_name,
                                raw_metadata=item,
                            )
        except Exception:
            pass
        return None
