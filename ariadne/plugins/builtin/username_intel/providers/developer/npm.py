"""NPM registry username intelligence provider."""

from typing import Optional
import aiohttp

from ariadne.plugins.builtin.username_intel.models import BaseUsernameProfile, DeveloperProfile
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider


class NpmProvider(BaseUsernameProvider):
    """Checks NPM maintainer profile."""

    @property
    def provider_name(self) -> str:
        return "NPM"

    @property
    def category(self) -> str:
        return "developer"

    @property
    def url_template(self) -> str:
        return "https://www.npmjs.com/~{username}"

    async def _check_api(self, session: aiohttp.ClientSession, username: str) -> Optional[BaseUsernameProfile]:
        api_url = f"https://registry.npmjs.org/-/v1/search?text=maintainer:{username}&size=1"
        try:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    total = data.get("total", 0)
                    if total > 0:
                        return DeveloperProfile(
                            username=username,
                            display_name=username,
                            profile_url=f"https://www.npmjs.com/~{username}",
                            is_present=True,
                            status_code=200,
                            confidence_score=0.96,
                            category=self.category,
                            platform_name=self.provider_name,
                            repositories_count=total,
                            raw_metadata={"total_packages": total},
                        )
        except Exception:
            pass
        return None
