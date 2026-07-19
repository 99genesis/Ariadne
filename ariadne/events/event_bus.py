"""Asynchronous Publish/Subscribe Event Bus implementation.

Ensures zero direct coupling between plugins and modules while providing fault
isolation so that an error in one listener does not crash the entire pipeline.
"""

import asyncio
import inspect
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Type
from ariadne.core.interfaces import EventListener, IEventBus, ILogger
from ariadne.events.topics import AriadneEvent


class AsyncEventBus(IEventBus):
    """Asynchronous Pub/Sub Event Bus with concurrent dispatch and exception isolation."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        """Initialize event bus.

        Args:
            logger: Optional logger for tracing event dispatches and errors.
        """
        self.logger = logger
        self._subscribers: Dict[Type[Any], Set[EventListener]] = defaultdict(set)
        self._global_subscribers: Set[EventListener] = set()

    def subscribe(self, event_type: Type[Any], listener: EventListener) -> None:
        """Subscribe an async listener to a specific event class type or global."""
        if event_type is AriadneEvent:
            self._global_subscribers.add(listener)
        else:
            self._subscribers[event_type].add(listener)

    def unsubscribe(self, event_type: Type[Any], listener: EventListener) -> None:
        """Remove a listener from subscriptions."""
        if event_type is AriadneEvent:
            self._global_subscribers.discard(listener)
        elif event_type in self._subscribers:
            self._subscribers[event_type].discard(listener)

    async def _safe_dispatch(self, listener: EventListener, event: Any) -> None:
        """Safely execute an async listener with error boundaries."""
        try:
            if inspect.iscoroutinefunction(listener):
                await listener(event)
            else:
                # Handle non-coroutine callable if registered accidentally
                res = listener(event)
                if inspect.isawaitable(res):
                    await res
        except Exception as exc:
            if self.logger:
                self.logger.error(
                    f"Event listener error during dispatch of '{type(event).__name__}': {exc}",
                    exc_info=exc,
                )

    async def publish(self, event: Any) -> None:
        """Publish an event concurrently to all matching subscribers."""
        event_type = type(event)
        listeners: Set[EventListener] = set(self._subscribers.get(event_type, set()))
        listeners.update(self._global_subscribers)

        # Also check parent classes if event inherits from an event class
        for reg_type, sub_set in self._subscribers.items():
            if reg_type is not event_type and isinstance(event, reg_type):
                listeners.update(sub_set)

        if not listeners:
            if self.logger:
                self.logger.debug(f"Event published with 0 subscribers: {event_type.__name__}")
            return

        if self.logger:
            self.logger.debug(
                f"Publishing event '{event_type.__name__}' to {len(listeners)} subscriber(s)"
            )

        tasks = [self._safe_dispatch(listener, event) for listener in listeners]
        await asyncio.gather(*tasks, return_exceptions=True)

    def clear_all_subscribers(self) -> None:
        """Clear all event bus subscriptions."""
        self._subscribers.clear()
        self._global_subscribers.clear()
