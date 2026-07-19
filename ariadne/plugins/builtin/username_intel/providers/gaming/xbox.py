"""Xbox Gamertag intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, GamingProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class XboxProvider(BaseUsernameProvider):
    """Checks Xbox Gamertag via profile check."""

    @property
    def provider_name(self) -> str:
        return "Xbox"

    @property
    def category(self) -> str:
        return "gaming"

    @property
    def url_template(self) -> str:
        return "https://xboxgamertag.com/search/{username}"
