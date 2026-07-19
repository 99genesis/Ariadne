"""Kaggle data science platform username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class KaggleProvider(BaseUsernameProvider):
    """Checks Kaggle profile."""

    @property
    def provider_name(self) -> str:
        return "Kaggle"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://www.kaggle.com/{username}"
