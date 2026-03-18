"""
timeline.py — Timeline-based turn system.

Each character has a timeline_position (float). Lower = acts sooner.
After acting, position increases by action_cost adjusted by speed.

Formula:
    new_position = current_position + action_cost / (1 + speed / 50)

Speed buff/debuff from haste/slow modifies effective speed.
"""

from __future__ import annotations

from typing import Optional

from pvp2.models import Character


def initialize_timeline(characters: list[Character]) -> list[Character]:
    """
    Set initial timeline positions based on speed.
    Faster characters start closer to 0 (act first).
    """
    for char in characters:
        effective_spd = char.get_effective_stat("spd")
        # Higher speed = lower initial position = acts first
        char.timeline_position = 1000.0 / max(1.0, effective_spd)
    return sorted(characters, key=lambda c: c.timeline_position)


def get_next_actor(characters: list[Character]) -> Optional[Character]:
    """Get the character with the lowest timeline position who is alive."""
    alive = [c for c in characters if c.is_alive]
    if not alive:
        return None
    return min(alive, key=lambda c: c.timeline_position)


def advance_timeline(character: Character, action_cost: int = 100) -> float:
    """
    Advance a character's timeline position after acting.

    Formula: new_pos = current + action_cost / (1 + effective_spd / 50)
    """
    effective_spd = character.get_effective_stat("spd")
    speed_factor = 1.0 + max(0.0, effective_spd) / 50.0
    advance = action_cost / speed_factor
    character.timeline_position += advance
    return character.timeline_position


def grant_extra_turn(character: Character, cost_reduction: int = 50) -> None:
    """
    Grant a character an extra turn by reducing their timeline position.
    Used for kill chains, crits, etc.
    """
    effective_spd = character.get_effective_stat("spd")
    speed_factor = 1.0 + max(0.0, effective_spd) / 50.0
    reduction = cost_reduction / speed_factor
    character.timeline_position = max(0.0, character.timeline_position - reduction)


def get_turn_order(characters: list[Character], count: int = 5) -> list[Character]:
    """
    Preview the next N characters in turn order.
    Does not modify positions.
    """
    alive = [c for c in characters if c.is_alive]
    alive_sorted = sorted(alive, key=lambda c: c.timeline_position)
    return alive_sorted[:count]


def normalize_timeline(characters: list[Character]) -> None:
    """
    Normalize timeline positions to prevent float overflow.
    Subtracts the minimum position from all characters.
    """
    alive = [c for c in characters if c.is_alive]
    if not alive:
        return
    min_pos = min(c.timeline_position for c in alive)
    if min_pos > 100.0:
        for c in alive:
            c.timeline_position -= min_pos
