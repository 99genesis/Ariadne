"""Plug-and-play Provider SDK for rapid custom provider development."""

from ariadne.providers.sdk.base import BaseDynamicProvider, ProviderCapabilityManifest
from ariadne.providers.sdk.social_graph import SocialGraphCollector

__all__ = ["BaseDynamicProvider", "ProviderCapabilityManifest", "SocialGraphCollector"]
