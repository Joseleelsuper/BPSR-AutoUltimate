"""Observer / EventBus — decouples network ↔ GUI ↔ input layers.

Usage:
    bus = EventBus.instance()
    bus.subscribe("group_update", my_callback)
    bus.emit("group_update", data)
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional


Callback = Callable[..., Any]


class EventBus:
    """Thread-safe publish/subscribe event bus."""

    _instance: Optional["EventBus"] = None

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callback]] = defaultdict(list)
        self._lock = threading.Lock()

    @classmethod
    def instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def subscribe(self, event: str, callback: Callback) -> None:
        """Register a callback for an event type."""
        with self._lock:
            if callback not in self._subscribers[event]:
                self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callback) -> None:
        """Remove a callback for an event type."""
        with self._lock:
            try:
                self._subscribers[event].remove(callback)
            except ValueError:
                pass

    def unsubscribe_all(self, event: Optional[str] = None) -> None:
        """Remove all callbacks, optionally for a specific event only."""
        with self._lock:
            if event:
                self._subscribers.pop(event, None)
            else:
                self._subscribers.clear()

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Invoke all subscribers for an event.

        Exceptions in callbacks are caught and printed to avoid breaking
        the emitter chain.
        """
        with self._lock:
            callbacks = list(self._subscribers.get(event, []))
        for cb in callbacks:
            try:
                cb(*args, **kwargs)
            except Exception as exc:
                print(f"[EventBus] Error in handler for '{event}': {exc}")
