"""Tumblr microblogging username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, SocialProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class TumblrProvider(BaseUsernameProvider):
    """Checks Tumblr blog subdomain."""

    @property
    def provider_name(self) -> str:
        return "Tumblr"

    @property
    def category(self) -> str:
        return "social"

    @property
    def url_template(self) -> str:
        return "https://{username}.tumblr.com"
