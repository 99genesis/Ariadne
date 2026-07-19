"""Hacker News username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, ForumProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class HackerNewsProvider(BaseUsernameProvider):
    """Checks Hacker News account using Firebase API."""

    @property
    def provider_name(self) -> str:
        return "HackerNews"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://news.ycombinator.com/user?id={username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://hacker-news.firebaseio.com/v0/user/{username}.json"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict) and data.get("id"):
                        return ForumProfile(
                            username=username,
                            display_name=data.get("id"),
                            profile_url=f"https://news.ycombinator.com/user?id={username}",
                            is_present=True,
                            bio=data.get("about"),
                            created_at=str(data.get("created")),
                            status_code=200,
                            confidence_score=0.99,
                            category=self.category,
                            platform_name=self.provider_name,
                            reputation_score=data.get("karma"),
                            raw_metadata=data,
                        )
        except Exception:
            pass
        return None
