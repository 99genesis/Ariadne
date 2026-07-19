"""Keybase cryptographic identity provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class KeybaseProvider(BaseUsernameProvider):
    """Checks Keybase account using public lookup API."""

    @property
    def provider_name(self) -> str:
        return "Keybase"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://keybase.io/{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://keybase.io/_/api/1.0/user/lookup.json?username={username}"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("status", {})
                    them = data.get("them")
                    if status.get("code") == 0 and isinstance(them, list) and len(them) > 0 and them[0] is not None:
                        user = them[0]
                        profile = user.get("profile", {})
                        pictures = user.get("pictures", {}).get("primary", {})
                        return SocialProfile(
                            username=username,
                            display_name=profile.get("full_name") or username,
                            profile_url=f"https://keybase.io/{username}",
                            is_present=True,
                            avatar_url=pictures.get("url"),
                            bio=profile.get("bio"),
                            status_code=200,
                            confidence_score=0.99,
                            category=self.category,
                            platform_name=self.provider_name,
                            location_hint=profile.get("location"),
                            raw_metadata=user,
                        )
        except Exception:
            pass
        return None
