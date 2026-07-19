"""Mastodon decentralized social network username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class MastodonProvider(BaseUsernameProvider):
    """Checks Mastodon handle on mastodon.social instance using JSON API."""

    @property
    def provider_name(self) -> str:
        return "Mastodon"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://mastodon.social/@{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://mastodon.social/api/v1/accounts/lookup?acct={username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return SocialProfile(
                        username=username,
                        display_name=data.get("display_name") or username,
                        profile_url=data.get("url") or f"https://mastodon.social/@{username}",
                        is_present=True,
                        avatar_url=data.get("avatar"),
                        bio=data.get("note"),
                        created_at=data.get("created_at"),
                        status_code=200,
                        confidence_score=0.98,
                        category=self.category,
                        platform_name=self.provider_name,
                        followers_count=data.get("followers_count"),
                        following_count=data.get("following_count"),
                        posts_count=data.get("statuses_count"),
                        raw_metadata=data,
                    )
        except Exception:
            pass
        return None
