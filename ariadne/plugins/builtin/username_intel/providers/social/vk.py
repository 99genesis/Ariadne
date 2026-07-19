"""VK social network username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class VKProvider(BaseUsernameProvider):
    """Checks VK profile."""

    @property
    def provider_name(self) -> str:
        return "VK"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://vk.com/{username}"
