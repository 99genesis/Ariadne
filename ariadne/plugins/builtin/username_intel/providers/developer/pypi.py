"""PyPI package index username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class PyPIProvider(BaseUsernameProvider):
    """Checks PyPI user profile."""

    @property
    def provider_name(self) -> str:
        return "PyPI"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://pypi.org/user/{username}/"
