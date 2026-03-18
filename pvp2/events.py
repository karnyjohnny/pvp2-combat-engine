"""
events.py — Event system with hooks for combat.

Supported hooks:
    before_attack, after_attack, on_damage, on_heal, on_kill, on_death,
    on_turn_start, on_turn_end, on_apply_status, on_remove_status,
    on_crit, on_dodge, on_block, on_combo
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Optional

from pvp2.models import EventType


class EventBus:
    """Central event dispatcher for combat."""

    def __init__(self) -> None:
        self._listeners: dict[EventType, list[tuple[int, Callable[..., Any]]]] = defaultdict(list)
        # priority: lower = runs first

    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[..., Any],
        priority: int = 50,
    ) -> None:
        """Register a listener for an event type."""
        self._listeners[event_type].append((priority, callback))
        self._listeners[event_type].sort(key=lambda x: x[0])

    def unsubscribe(
        self,
        event_type: EventType,
        callback: Callable[..., Any],
    ) -> None:
        """Remove a listener."""
        self._listeners[event_type] = [
            (p, cb) for p, cb in self._listeners[event_type] if cb is not callback
        ]

    async def emit(self, event_type: EventType, **kwargs: Any) -> dict[str, Any]:
        """
        Emit an event to all listeners.

        Returns a dict of aggregated results from listeners.
        Listeners can modify kwargs in-place (e.g., modify damage).
        """
        results: dict[str, Any] = {}
        for _priority, callback in self._listeners.get(event_type, []):
            try:
                import asyncio
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(**kwargs)
                else:
                    result = callback(**kwargs)
                if isinstance(result, dict):
                    results.update(result)
            except Exception:
                pass  # don't let a listener crash the battle
        return results

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()

    def listener_count(self, event_type: Optional[EventType] = None) -> int:
        """Count registered listeners."""
        if event_type:
            return len(self._listeners.get(event_type, []))
        return sum(len(v) for v in self._listeners.values())
