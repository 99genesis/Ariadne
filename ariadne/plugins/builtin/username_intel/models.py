"""Pydantic domain models for Username Profile Intelligence using composition and inheritance.

Enforces strict schema validation for findings discovered across diverse platform categories.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BaseUsernameProfile(BaseModel):
    """Base domain model representing a verified or checked platform profile."""

    username: str = Field(..., description="Target username or handle")
    display_name: Optional[str] = Field(default=None, description="Parsed human display name")
    profile_url: str = Field(..., description="Canonical URL to the profile page")
    is_present: bool = Field(default=False, description="True if profile exists and is active")
    avatar_url: Optional[str] = Field(default=None, description="Direct URL to avatar image")
    bio: Optional[str] = Field(default=None, description="Extracted biography or about description")
    created_at: Optional[str] = Field(default=None, description="Account creation timestamp string")
    is_verified: bool = Field(default=False, description="Platform verification badge check")
    status_code: Optional[int] = Field(default=None, description="HTTP response code encountered")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability score [0.0-1.0]")
    category: str = Field(default="general", description="Platform category e.g. developer, social, gaming, forum")
    platform_name: str = Field(..., description="Display name of the platform e.g. GitHub, Instagram")
    error_message: Optional[str] = Field(default=None, description="Error reason if lookup failed")
    raw_metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw extracted JSON or meta tags")


class DeveloperProfile(BaseUsernameProfile):
    """Profile composition for software developer and engineering platforms."""

    repositories_count: Optional[int] = Field(default=None, description="Total public repositories or packages")
    stars_count: Optional[int] = Field(default=None, description="Total stars or upvotes earned")
    followers_count: Optional[int] = Field(default=None, description="Number of followers")
    following_count: Optional[int] = Field(default=None, description="Number of accounts followed")
    organizations: List[str] = Field(default_factory=list, description="Associated organizations or groups")
    languages_used: List[str] = Field(default_factory=list, description="Primary programming languages used")


class SocialProfile(BaseUsernameProfile):
    """Profile composition for social media and blogging networks."""

    posts_count: Optional[int] = Field(default=None, description="Number of posts, tweets, or videos")
    followers_count: Optional[int] = Field(default=None, description="Follower count")
    following_count: Optional[int] = Field(default=None, description="Following count")
    external_links: List[str] = Field(default_factory=list, description="External links extracted from bio e.g. Linktree")
    location_hint: Optional[str] = Field(default=None, description="Geographic location string if provided")


class GamingProfile(BaseUsernameProfile):
    """Profile composition for gaming and entertainment platforms."""

    level: Optional[int] = Field(default=None, description="Account level or XP tier")
    games_owned_count: Optional[int] = Field(default=None, description="Total library size")
    friends_count: Optional[int] = Field(default=None, description="Number of friends")
    is_online: Optional[bool] = Field(default=None, description="Whether user is currently online or ingame")


class ForumProfile(BaseUsernameProfile):
    """Profile composition for technical forums and community boards."""

    messages_count: Optional[int] = Field(default=None, description="Total forum posts or comments")
    solutions_count: Optional[int] = Field(default=None, description="Marked accepted answers or solutions")
    reputation_score: Optional[int] = Field(default=None, description="Reputation points or reaction count")
    rank_title: Optional[str] = Field(default=None, description="Community rank or role title")


class InviteProfile(BaseUsernameProfile):
    """Profile composition for server invites and chat platforms e.g. Discord."""

    guild_name: Optional[str] = Field(default=None, description="Name of the server or guild")
    member_count: Optional[int] = Field(default=None, description="Total members in server")
    online_count: Optional[int] = Field(default=None, description="Active online members count")
    channel_name: Optional[str] = Field(default=None, description="Channel invite destination")
    banner_url: Optional[str] = Field(default=None, description="Server banner background URL")
