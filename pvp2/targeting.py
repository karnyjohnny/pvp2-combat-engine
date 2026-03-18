"""
targeting.py — AI targeting module with priority-based rules.

Strategies:
    lowest_hp      — target with least HP
    highest_threat — target with highest threat score
    healer_first   — prioritize healers (characters with heal skills)
    random         — random target
    taunt_aware    — must target taunter if present

Priority chain: taunt > specific strategy > fallback
"""

from __future__ import annotations

import random as _random
from typing import Optional

from pvp2.effects import get_taunter
from pvp2.models import Character, TargetType


def select_target(
    attacker: Character,
    enemies: list[Character],
    allies: list[Character],
    target_type: TargetType,
    strategy: str = "lowest_hp",
    seed: Optional[int] = None,
) -> list[Character]:
    """
    Select target(s) based on target type and strategy.

    Returns list of target characters.
    """
    rng = _random.Random(seed) if seed else _random.Random()

    if target_type == TargetType.SELF:
        return [attacker]

    if target_type == TargetType.ALL_ENEMIES:
        return [e for e in enemies if e.is_alive]

    if target_type == TargetType.ALL_ALLIES:
        return [a for a in allies if a.is_alive]

    if target_type == TargetType.SINGLE_ALLY:
        alive_allies = [a for a in allies if a.is_alive]
        if not alive_allies:
            return []
        if strategy == "lowest_hp":
            return [min(alive_allies, key=lambda c: c.stats.hp)]
        return [rng.choice(alive_allies)]

    # Single enemy / random enemy targeting
    alive_enemies = [e for e in enemies if e.is_alive]
    if not alive_enemies:
        return []

    # Taunt check — must target taunter if present
    taunter = get_taunter(alive_enemies)
    if taunter:
        return [taunter]

    if target_type == TargetType.RANDOM_ENEMY:
        return [rng.choice(alive_enemies)]

    # Apply strategy
    return [_apply_strategy(alive_enemies, strategy, rng)]


def _apply_strategy(
    candidates: list[Character],
    strategy: str,
    rng: _random.Random,
) -> Character:
    """Apply a targeting strategy to select one character."""
    if not candidates:
        raise ValueError("No candidates for targeting")

    if strategy == "lowest_hp":
        return min(candidates, key=lambda c: c.stats.hp)

    elif strategy == "highest_threat":
        return max(candidates, key=lambda c: c.threat)

    elif strategy == "healer_first":
        healers = [
            c for c in candidates
            if any(
                any(e.effect_type == "heal" for e in s.effects)
                for s in c.skills
            )
        ]
        if healers:
            return min(healers, key=lambda c: c.stats.hp)
        return min(candidates, key=lambda c: c.stats.hp)

    elif strategy == "highest_hp":
        return max(candidates, key=lambda c: c.stats.hp)

    elif strategy == "random":
        return rng.choice(candidates)

    # Default: lowest HP
    return min(candidates, key=lambda c: c.stats.hp)


def build_priority_chain(*strategies: str) -> list[str]:
    """Build a priority chain of targeting strategies."""
    return list(strategies)


def select_with_priority_chain(
    attacker: Character,
    enemies: list[Character],
    allies: list[Character],
    target_type: TargetType,
    priority_chain: list[str],
    seed: Optional[int] = None,
) -> list[Character]:
    """
    Try strategies in order until one returns a valid target.
    """
    for strategy in priority_chain:
        targets = select_target(attacker, enemies, allies, target_type, strategy, seed)
        if targets:
            return targets
    # Ultimate fallback
    return select_target(attacker, enemies, allies, target_type, "random", seed)
