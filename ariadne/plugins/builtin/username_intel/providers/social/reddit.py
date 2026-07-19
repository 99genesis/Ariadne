"""Reddit social platform username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class RedditProvider(BaseUsernameProvider):
    """Checks Reddit user using JSON endpoint and HTML fallback."""

    @property
    def provider_name(self) -> str:
        return "Reddit"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://www.reddit.com/user/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://www.reddit.com/user/{username}/about.json"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user = data.get("data", {})
                    if user.get("name"):
                        return SocialProfile(
                            username=username,
                            display_name=user.get("subreddit", {}).get("title") or username,
                            profile_url=f"https://www.reddit.com/user/{username}",
                            is_present=True,
                            avatar_url=user.get("icon_img"),
                            bio=user.get("subreddit", {}).get("public_description"),
                            created_at=str(user.get("created_utc")),
                            status_code=200,
                            confidence_score=0.99,
                            category=self.category,
                            platform_name=self.provider_name,
                            raw_metadata=user,
                        )
                elif resp.status == 404:
                    return None
        except Exception:
            pass
        return None
