"""Medium publishing platform username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class MediumProvider(BaseUsernameProvider):
    """Checks Medium author profile."""

    @property
    def provider_name(self) -> str:
        return "Medium"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://medium.com/@{username}"
