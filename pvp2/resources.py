"""
resources.py — Resource systems: mana, rage, energy, ultimate charge.
"""

from __future__ import annotations

from pvp2.models import Character, ResourceType


def get_resource(character: Character, res_type: ResourceType) -> int:
    """Get current resource value."""
    if res_type == ResourceType.MANA:
        return character.stats.mana
    elif res_type == ResourceType.RAGE:
        return character.stats.rage
    elif res_type == ResourceType.ENERGY:
        return character.stats.energy
    return 0


def get_max_resource(character: Character, res_type: ResourceType) -> int:
    """Get max resource value."""
    if res_type == ResourceType.MANA:
        return character.stats.max_mana
    elif res_type == ResourceType.RAGE:
        return character.stats.max_rage
    elif res_type == ResourceType.ENERGY:
        return character.stats.max_energy
    return 0


def spend_resource(character: Character, res_type: ResourceType, amount: int) -> bool:
    """
    Spend resource. Returns True if sufficient, False otherwise.
    """
    current = get_resource(character, res_type)
    if current < amount:
        return False

    if res_type == ResourceType.MANA:
        character.stats.mana -= amount
    elif res_type == ResourceType.RAGE:
        character.stats.rage -= amount
    elif res_type == ResourceType.ENERGY:
        character.stats.energy -= amount
    return True


def restore_resource(character: Character, res_type: ResourceType, amount: int) -> int:
    """Restore resource. Returns actual amount restored."""
    max_val = get_max_resource(character, res_type)
    current = get_resource(character, res_type)
    actual = min(amount, max_val - current)

    if res_type == ResourceType.MANA:
        character.stats.mana += actual
    elif res_type == ResourceType.RAGE:
        character.stats.rage += actual
    elif res_type == ResourceType.ENERGY:
        character.stats.energy += actual
    return actual


def gain_ultimate_charge(character: Character, amount: int) -> int:
    """Add ultimate charge. Returns actual amount gained."""
    old = character.stats.ultimate_charge
    character.stats.ultimate_charge = min(
        character.stats.max_ultimate_charge,
        character.stats.ultimate_charge + amount,
    )
    return character.stats.ultimate_charge - old


def can_use_ultimate(character: Character) -> bool:
    """Check if ultimate is fully charged."""
    return character.stats.ultimate_charge >= character.stats.max_ultimate_charge


def spend_ultimate(character: Character) -> bool:
    """Spend full ultimate charge. Returns True if was full."""
    if not can_use_ultimate(character):
        return False
    character.stats.ultimate_charge = 0
    return True


def regen_resources_on_turn(character: Character) -> dict[str, int]:
    """
    Natural resource regeneration at turn start.
    Mana: +5/turn, Energy: +15/turn, Rage: -5/turn (decays)
    """
    restored: dict[str, int] = {}

    mana_regen = restore_resource(character, ResourceType.MANA, 5)
    if mana_regen > 0:
        restored["mana"] = mana_regen

    energy_regen = restore_resource(character, ResourceType.ENERGY, 15)
    if energy_regen > 0:
        restored["energy"] = energy_regen

    # Rage decays
    if character.stats.rage > 0:
        decay = min(5, character.stats.rage)
        character.stats.rage -= decay
        restored["rage_decay"] = decay

    return restored


def gain_rage_on_hit(character: Character, damage_dealt: int) -> int:
    """Gain rage proportional to damage dealt."""
    rage_gain = min(15, max(3, damage_dealt // 20))
    return restore_resource(character, ResourceType.RAGE, rage_gain)


def gain_rage_on_damage_taken(character: Character, damage_taken: int) -> int:
    """Gain rage when taking damage."""
    rage_gain = min(10, max(2, damage_taken // 25))
    return restore_resource(character, ResourceType.RAGE, rage_gain)
