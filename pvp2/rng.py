"""
rng.py — Controlled RNG system with luck, accuracy, evasion influence.

Formulas:
=========

Hit chance:
    effective_hit = base_accuracy + (luck * 0.3) - target_evasion - (target_luck * 0.15)
    clamped to [5%, 99%]

Crit chance:
    effective_crit = base_crit + (luck * 0.5)
    clamped to [1%, balance.MAX_CRIT_CHANCE]

Status application:
    effective_chance = base_chance * (1 + luck * 0.01) * (1 - target_luck * 0.005)
    clamped to [5%, 95%]

Damage variance:
    multiplier = uniform(0.90, 1.10) biased by luck:
        if luck > 50: lower bound shifts up by (luck - 50) * 0.001
"""

from __future__ import annotations

import hashlib
import random
from typing import Optional


def _seeded_random(seed: Optional[int] = None) -> random.Random:
    """Create a Random instance with optional seed."""
    if seed is not None:
        return random.Random(seed)
    return random.Random()


def roll(chance: float, seed: Optional[int] = None) -> bool:
    """
    Roll with a given chance (0-100). Returns True if success.

    Args:
        chance: Probability of success (0-100).
        seed: Optional deterministic seed.
    """
    rng = _seeded_random(seed)
    return rng.random() * 100.0 < chance


def roll_value(min_val: float, max_val: float, seed: Optional[int] = None) -> float:
    """Roll a value in range [min_val, max_val]."""
    rng = _seeded_random(seed)
    return rng.uniform(min_val, max_val)


def hit_check(
    accuracy: float,
    attacker_luck: float,
    target_evasion: float,
    target_luck: float,
    seed: Optional[int] = None,
) -> bool:
    """
    Determine if an attack hits.

    Formula:
        effective_hit = accuracy + (luck * 0.3) - evasion - (target_luck * 0.15)
    """
    effective = accuracy + (attacker_luck * 0.3) - target_evasion - (target_luck * 0.15)
    effective = max(5.0, min(99.0, effective))
    return roll(effective, seed)


def crit_check(
    crit_chance: float,
    attacker_luck: float,
    max_crit: float = 75.0,
    seed: Optional[int] = None,
) -> bool:
    """
    Determine if an attack is a critical hit.

    Formula:
        effective_crit = crit_chance + (luck * 0.5)
    """
    effective = crit_chance + (attacker_luck * 0.5)
    effective = max(1.0, min(max_crit, effective))
    return roll(effective, seed)


def status_apply_check(
    base_chance: float,
    attacker_luck: float,
    target_luck: float,
    seed: Optional[int] = None,
) -> bool:
    """
    Determine if a status effect is successfully applied.

    Formula:
        effective = base_chance * (1 + attacker_luck * 0.01) * (1 - target_luck * 0.005)
    """
    effective = base_chance * (1.0 + attacker_luck * 0.01) * (1.0 - target_luck * 0.005)
    effective = max(5.0, min(95.0, effective))
    return roll(effective, seed)


def damage_variance(luck: float, seed: Optional[int] = None) -> float:
    """
    Calculate damage variance multiplier.

    Base range: [0.90, 1.10]
    Luck > 50 shifts lower bound up: lower = 0.90 + (luck - 50) * 0.001
    """
    rng = _seeded_random(seed)
    lower = 0.90
    if luck > 50:
        lower = min(0.95, 0.90 + (luck - 50) * 0.001)
    return rng.uniform(lower, 1.10)


def generate_battle_seed(user_ids: list[int], timestamp: Optional[float] = None) -> int:
    """Generate a deterministic seed from user IDs and timestamp."""
    import time as _time
    ts = timestamp or _time.time()
    data = f"{sorted(user_ids)}:{ts}"
    return int(hashlib.sha256(data.encode()).hexdigest()[:8], 16)
