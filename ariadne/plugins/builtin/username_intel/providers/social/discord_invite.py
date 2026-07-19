"""Discord invite code and vanity URL intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, InviteProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class DiscordInviteProvider(BaseUsernameProvider):
    """Checks Discord vanity invite code using API."""

    @property
    def provider_name(self) -> str:
        return "DiscordInvite"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://discord.gg/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://discord.com/api/v9/invites/{username}?with_counts=true"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    guild = data.get("guild", {})
                    channel = data.get("channel", {})
                    banner = guild.get("banner")
                    banner_url = f"https://cdn.discordapp.com/banners/{guild.get('id')}/{banner}.png" if banner else None
                    icon = guild.get("icon")
                    icon_url = f"https://cdn.discordapp.com/icons/{guild.get('id')}/{icon}.png" if icon else None

                    return InviteProfile(
                        username=username,
                        display_name=guild.get("name") or username,
                        profile_url=f"https://discord.gg/{username}",
                        is_present=True,
                        avatar_url=icon_url,
                        bio=guild.get("description"),
                        status_code=200,
                        confidence_score=0.99,
                        category=self.category,
                        platform_name=self.provider_name,
                        guild_name=guild.get("name"),
                        member_count=data.get("approximate_member_count"),
                        online_count=data.get("approximate_presence_count"),
                        channel_name=channel.get("name"),
                        banner_url=banner_url,
                        raw_metadata=data,
                    )
        except Exception:
            pass
        return None
