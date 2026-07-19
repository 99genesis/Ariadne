"""YouTube channel username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class YouTubeProvider(BaseUsernameProvider):
    """Checks YouTube channel handle (@username)."""

    @property
    def provider_name(self) -> str:
        return "YouTube"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://www.youtube.com/@{username}"
