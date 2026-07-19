"""IP & Domain Intelligence Plugin implementing IPlugin."""

import dns.resolver
from typing import Any, Dict, List
import aiohttp

from ariadne.core.interfaces import IEventBus, IPlugin, IProvider
from ariadne.core.models import IntelligenceResult, TargetEntity, TargetType


class IPDomainIntelPlugin(IPlugin):
    """Resolves domain records and retrieves IP Geolocation/ASN data."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.event_bus: IEventBus | None = None

    @property
    def plugin_id(self) -> str:
        return "ariadne.builtin.ip_domain_intel"

    async def initialize(self, config: Dict[str, Any], event_bus: IEventBus) -> bool:
        self.config = config
        self.event_bus = event_bus
        return True

    async def can_handle(self, target: TargetEntity) -> bool:
        return target.target_type in (TargetType.IP, TargetType.DOMAIN, TargetType.ORGANIZATION) or any(
            k in target.metadata for k in ("ip", "domain")
        )

    def _resolve_dns(self, domain: str) -> Dict[str, List[str]]:
        records: Dict[str, List[str]] = {}
        for rtype in ["A", "MX", "NS", "TXT"]:
            try:
                answers = dns.resolver.resolve(domain, rtype)
                records[rtype] = [str(a) for a in answers]
            except Exception:
                records[rtype] = []
        return records

    async def _lookup_ip_geo(self, ip: str) -> Dict[str, Any]:
        url = f"http://ip-api.com/json/{ip}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return dict(await resp.json())
            except Exception:
                pass
        return {"country": "Unknown", "city": "Unknown", "isp": "Unknown", "as": "AS_UNKNOWN"}

    async def execute(self, target: TargetEntity, providers: Dict[str, IProvider]) -> List[IntelligenceResult]:
        results: List[IntelligenceResult] = []

        domain = target.metadata.get("domain") or (target.display_name if target.target_type == TargetType.DOMAIN else "")
        if domain:
            dns_data = self._resolve_dns(domain)
            ip_list = dns_data.get("A", [])
            links = [f"[[Domain_{domain}]]"]
            for ip in ip_list:
                links.append(f"[[IP_{ip}]]")

            results.append(
                IntelligenceResult(
                    title=f"DNS ve Ağ Kayıtları: {domain}",
                    entity_type="domain",
                    source_plugin=self.plugin_id,
                    confidence_score=1.0,
                    tags=["#osint/dns", "#network/domain"],
                    links_to=links,
                    metadata={"domain": domain, "dns_records": dns_data},
                    content_markdown=f"### DNS Enumeration ({domain})\n- **A Records:** `{dns_data.get('A', [])}`\n- **MX Records:** `{dns_data.get('MX', [])}`\n- **NS Records:** `{dns_data.get('NS', [])}`\n",
                )
            )

            # If resolved an IP, run geo lookup on primary IP
            if ip_list:
                target.metadata["ip"] = ip_list[0]

        ip = target.metadata.get("ip") or (target.display_name if target.target_type == TargetType.IP else "")
        if ip:
            geo_data = await self._lookup_ip_geo(ip)
            city = geo_data.get("city", "Unknown")
            country = geo_data.get("country", "Unknown")
            asn = str(geo_data.get("as", "AS_UNKNOWN")).split(" ")[0]

            results.append(
                IntelligenceResult(
                    title=f"IP Geolocation & ASN Bilgisi: {ip}",
                    entity_type="ip",
                    source_plugin=self.plugin_id,
                    confidence_score=0.95,
                    tags=["#osint/ip", f"#country/{country.lower()}" if country != "Unknown" else "#country/unknown"],
                    links_to=[f"[[IP_{ip}]]", f"[[ASN_{asn}]]", f"[[Location_{city.replace(' ', '_')}]]"],
                    metadata={"ip": ip, "geo_details": geo_data},
                    content_markdown=f"### Network IP Geolocation\n- **IP Address:** `{ip}`\n- **Country / City:** `{country} - {city}`\n- **ISP / ASN:** `{geo_data.get('isp', 'Unknown')} ({asn})`\n",
                )
            )

        return results

    async def cleanup(self) -> None:
        pass


def get_plugin() -> IPlugin:
    return IPDomainIntelPlugin()
