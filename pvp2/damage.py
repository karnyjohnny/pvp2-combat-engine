"""
damage.py — Complete damage formula.

Damage Formula:
===============
1. base_damage = skill_power + (scaling_stat * scaling_ratio)
2. variance = base_damage * damage_variance(luck)  -> [0.90-1.10]
3. crit_multiplier = crit_dmg / 100 if crit else 1.0
4. element_bonus = 1.0 - (target_resistance / 100)  (clamped to [0.25, 2.0])
5. defense_mitigation = 1.0 - (defense / (defense + 100))  -> asymptotic, never 0
6. raw_damage = variance * crit_multiplier * element_bonus * defense_mitigation
7. shield_absorbed = min(raw_damage, shield_amount)
8. final_damage = max(1, raw_damage - shield_absorbed)

Healing Formula:
================
1. base_heal = skill_power + (scaling_stat * scaling_ratio)
2. variance = base_heal * damage_variance(luck)
3. final_heal = max(1, variance)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pvp2 import rng
from pvp2.models import Character, Element, SkillEffect, StatusType


@dataclass
class DamageResult:
    """Result of a damage calculation."""
    raw_damage: int = 0
    final_damage: int = 0
    shield_absorbed: int = 0
    is_critical: bool = False
    is_dodged: bool = False
    element: Element = Element.PHYSICAL
    overkill: int = 0
    lifesteal_heal: int = 0
    reflected_damage: int = 0
    variance_roll: float = 1.0


def calculate_damage(
    attacker: Character,
    target: Character,
    effect: SkillEffect,
    is_critical: bool = False,
    combo_bonus: float = 0.0,
    seed: Optional[int] = None,
) -> DamageResult:
    """
    Calculate damage from an attack effect.

    Full pipeline:
    1. Base damage from skill power + stat scaling
    2. Damage variance (luck-influenced)
    3. Critical hit multiplier
    4. Elemental resistance
    5. Defense mitigation (asymptotic)
    6. Combo bonus
    7. Shield absorption
    8. Lifesteal calculation
    9. Reflect calculation
    """
    result = DamageResult(element=effect.element)

    # Step 1: Base damage
    scaling_stat_value = attacker.get_effective_stat(effect.scaling_stat)
    base_damage = effect.power + (scaling_stat_value * effect.scaling_ratio)

    # Step 2: Variance
    variance = rng.damage_variance(attacker.stats.luck, seed)
    result.variance_roll = variance
    damage = base_damage * variance

    # Step 3: Critical hit
    if is_critical:
        result.is_critical = True
        crit_mult = attacker.get_effective_stat("crit_dmg") / 100.0
        damage *= crit_mult

    # Step 4: Elemental resistance
    if effect.element != Element.PHYSICAL:
        resistance = target.stats.get_resistance(effect.element)
        resistance = max(-100.0, min(75.0, resistance))  # cap resistance
        element_mult = 1.0 - (resistance / 100.0)
        element_mult = max(0.25, min(2.0, element_mult))
        damage *= element_mult

    # Step 5: Defense mitigation
    if effect.scaling_stat in ("atk",):
        defense = max(0, target.get_effective_stat("defense"))
    else:
        defense = max(0, target.get_effective_stat("mdef"))
    mitigation = 1.0 - (defense / (defense + 100.0))
    mitigation = max(0.1, mitigation)  # minimum 10% damage gets through
    damage *= mitigation

    # Step 6: Combo bonus
    if combo_bonus > 0:
        damage *= (1.0 + combo_bonus)

    raw_damage = max(1, int(damage))
    result.raw_damage = raw_damage

    # Step 7: Shield absorption
    shields = target.get_statuses(StatusType.SHIELD)
    remaining_damage = raw_damage
    total_absorbed = 0

    for shield in shields:
        if remaining_damage <= 0:
            break
        absorbed = min(remaining_damage, int(shield.shield_amount))
        shield.shield_amount -= absorbed
        total_absorbed += absorbed
        remaining_damage -= absorbed
        if shield.shield_amount <= 0:
            target.statuses.remove(shield)

    result.shield_absorbed = total_absorbed
    result.final_damage = max(1, remaining_damage) if remaining_damage > 0 else 0

    # Overkill
    if result.final_damage > target.stats.hp:
        result.overkill = result.final_damage - target.stats.hp

    # Step 8: Lifesteal
    lifesteal_statuses = attacker.get_statuses(StatusType.LIFESTEAL)
    if lifesteal_statuses:
        lifesteal_pct = sum(s.power for s in lifesteal_statuses)
        lifesteal_pct = min(lifesteal_pct, 40.0)  # cap
        result.lifesteal_heal = int(result.final_damage * lifesteal_pct / 100.0)

    # Step 9: Reflect
    reflect_statuses = target.get_statuses(StatusType.REFLECT)
    if reflect_statuses:
        reflect_pct = sum(s.power for s in reflect_statuses)
        reflect_pct = min(reflect_pct, 30.0)  # cap
        result.reflected_damage = int(result.raw_damage * reflect_pct / 100.0)

    return result


def calculate_healing(
    healer: Character,
    target: Character,
    effect: SkillEffect,
    seed: Optional[int] = None,
) -> int:
    """Calculate healing amount."""
    scaling_stat_value = healer.get_effective_stat(effect.scaling_stat)
    base_heal = effect.power + (scaling_stat_value * effect.scaling_ratio)
    variance = rng.damage_variance(healer.stats.luck, seed)
    return max(1, int(base_heal * variance))


def apply_damage(target: Character, damage: int) -> bool:
    """
    Apply damage to a character. Returns True if character dies.
    """
    target.stats.hp = max(0, target.stats.hp - damage)
    if target.stats.hp <= 0:
        target.is_alive = False
        return True
    # Wake up from sleep on damage
    target.statuses = [
        s for s in target.statuses if s.status_type != StatusType.SLEEP
    ]
    return False


def apply_healing(target: Character, amount: int) -> int:
    """Apply healing to a character. Returns actual amount healed."""
    old_hp = target.stats.hp
    target.stats.hp = min(target.stats.max_hp, target.stats.hp + amount)
    return target.stats.hp - old_hp
