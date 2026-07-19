"""Dependency Injection Container for Ariadne OSINT Framework.

Provides centralized registration and resolution of Singleton, Scoped, and Transient
services following the Dependency Inversion Principle.
"""

from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from ariadne.core.exceptions import DependencyResolutionException

T = TypeVar("T")


class ServiceLifetime(str, Enum):
    """Service registration lifetime scopes."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"


class DIContainer:
    """Dependency Injection Container supporting interface-to-implementation mapping."""

    def __init__(self) -> None:
        """Initialize empty registry tables."""
        self._factories: Dict[Type[Any], Callable[["DIContainer"], Any]] = {}
        self._lifetimes: Dict[Type[Any], ServiceLifetime] = {}
        self._singletons: Dict[Type[Any], Any] = {}

    def register(
        self,
        interface_or_type: Type[T],
        factory: Callable[["DIContainer"], T],
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> None:
        """Register a factory or constructor for a given interface or class type.

        Args:
            interface_or_type: The protocol, interface, or class key.
            factory: Callable accepting DIContainer and returning an instance of T.
            lifetime: SINGLETON (cached) or TRANSIENT (new instance every time).
        """
        self._factories[interface_or_type] = factory
        self._lifetimes[interface_or_type] = lifetime

    def register_instance(self, interface_or_type: Type[T], instance: T) -> None:
        """Register an existing pre-built instance as a Singleton.

        Args:
            interface_or_type: Key type.
            instance: Concrete instance object.
        """
        self._singletons[interface_or_type] = instance
        self._lifetimes[interface_or_type] = ServiceLifetime.SINGLETON

    def resolve(self, interface_or_type: Type[T]) -> T:
        """Resolve an instance for the requested interface or type.

        Args:
            interface_or_type: The protocol, interface, or class key to resolve.

        Returns:
            An instance implementing the requested type.

        Raises:
            DependencyResolutionException: If the type is not registered.
        """
        if interface_or_type in self._singletons:
            resolved_instance: T = self._singletons[interface_or_type]
            return resolved_instance

        factory = self._factories.get(interface_or_type)
        if not factory:
            raise DependencyResolutionException(service_name=str(interface_or_type))

        try:
            instance = factory(self)
        except Exception as exc:
            import logging
            logging.getLogger("Ariadne.DI").error(
                f"Error resolving service '{interface_or_type}' from DI container.",
                exc_info=True
            )
            raise DependencyResolutionException(service_name=str(interface_or_type)) from exc

        if self._lifetimes.get(interface_or_type) == ServiceLifetime.SINGLETON:
            self._singletons[interface_or_type] = instance

        return instance

    def is_registered(self, interface_or_type: Type[Any]) -> bool:
        """Check if a service is registered in the container."""
        return interface_or_type in self._factories or interface_or_type in self._singletons

    def clear(self) -> None:
        """Clear all registered services and singleton caches."""
        self._factories.clear()
        self._lifetimes.clear()
        self._singletons.clear()


# Global default container instance for application bootstrapping
container = DIContainer()
