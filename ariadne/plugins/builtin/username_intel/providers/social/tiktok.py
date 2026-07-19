"""TikTok video platform username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class TikTokProvider(BaseUsernameProvider):
    """Checks TikTok handle."""

    @property
    def provider_name(self) -> str:
        return "TikTok"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://www.tiktok.com/@{username}"
