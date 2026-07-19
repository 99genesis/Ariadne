"""Ariadne CLI Command System following Linux CLI philosophy and Command pattern."""

from ariadne.commands.base import BaseCommand
from ariadne.commands.registry import CommandRegistry

__all__ = ["BaseCommand", "CommandRegistry"]
