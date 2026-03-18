"""
effects.py — Effects & Status Engine.

Handles application, ticking, removal, and interaction of all status effects:
buff, debuff, DOT, HOT, shield, taunt, stun, immobilize, silence, sleep,
petrify, regen, lifesteal, reflect, charm, bleed, burn, freeze, shock, haste, slow, poison.
"""

from __future__ import annotations

from typing import Optional

from pvp2 import rng
from pvp2.models import Character, Element, EventType, StatusEffect, StatusType


def apply_status(
    target: Character,
    effect: StatusEffect,
    attacker_luck: float = 10.0,
    target_luck: float = 10.0,
    seed: Optional[int] = None,
) -> bool:
    """
    Attempt to apply a status effect to a target.
    Returns True if successfully applied.
    """
    # Check application chance with luck influence
    if effect.chance_to_apply < 100.0:
        if not rng.status_apply_check(effect.chance_to_apply, attacker_luck, target_luck, seed):
            return False

    # Petrify/Freeze immunity: can't stack hard CC
    hard_cc = (StatusType.STUN, StatusType.PETRIFY, StatusType.FREEZE)
    if effect.status_type in hard_cc:
        if any(s.status_type in hard_cc for s in target.statuses):
            return False  # already hard CC'd

    # Handle stacking
    existing = [s for s in target.statuses if s.name == effect.name]
    if existing and not effect.stackable:
        # Refresh duration
        existing[0].duration = max(existing[0].duration, effect.duration)
        existing[0].power = max(existing[0].power, effect.power)
        if effect.shield_amount > 0:
            existing[0].shield_amount = max(existing[0].shield_amount, effect.shield_amount)
        return True

    if existing and effect.stackable:
        if existing[0].current_stacks < effect.max_stacks:
            existing[0].current_stacks += 1
            existing[0].duration = max(existing[0].duration, effect.duration)
            existing[0].power += effect.power
            return True
        else:
            # Max stacks, just refresh duration
            existing[0].duration = max(existing[0].duration, effect.duration)
            return True

    # Apply new status
    import copy
    new_effect = copy.deepcopy(effect)
    target.statuses.append(new_effect)
    return True


def remove_status(target: Character, status_name: str) -> Optional[StatusEffect]:
    """Remove a status effect by name. Returns removed effect or None."""
    for i, s in enumerate(target.statuses):
        if s.name == status_name:
            return target.statuses.pop(i)
    return None


def remove_statuses_by_type(target: Character, status_type: StatusType) -> list[StatusEffect]:
    """Remove all statuses of a given type."""
    removed = [s for s in target.statuses if s.status_type == status_type]
    target.statuses = [s for s in target.statuses if s.status_type != status_type]
    return removed


def tick_statuses(character: Character) -> list[dict]:
    """
    Process all status effects for one turn tick.
    Returns list of events (damage/heal ticks, expired statuses).
    """
    events: list[dict] = []
    expired: list[StatusEffect] = []

    for status in character.statuses:
        # DOT tick
        if status.status_type in (StatusType.DOT, StatusType.BLEED, StatusType.BURN, StatusType.POISON):
            tick_dmg = int(status.tick_damage * status.current_stacks)
            if tick_dmg > 0:
                character.stats.hp = max(0, character.stats.hp - tick_dmg)
                events.append({
                    "type": "dot_tick",
                    "name": status.name,
                    "damage": tick_dmg,
                    "emoji": status.emoji,
                    "target": character.name,
                })
                if character.stats.hp <= 0:
                    character.is_alive = False

        # HOT / Regen tick
        if status.status_type in (StatusType.HOT, StatusType.REGEN):
            tick_heal = int(status.tick_heal * status.current_stacks)
            if tick_heal > 0:
                old_hp = character.stats.hp
                character.stats.hp = min(character.stats.max_hp, character.stats.hp + tick_heal)
                actual = character.stats.hp - old_hp
                if actual > 0:
                    events.append({
                        "type": "hot_tick",
                        "name": status.name,
                        "heal": actual,
                        "emoji": status.emoji,
                        "target": character.name,
                    })

        # Shock: chance to lose turn (handled in combat.py via prevents_action)
        # Burn: extra fire damage (already in tick_damage)
        # Bleed: physical DOT (already in tick_damage)
        # Freeze: skip turn + take extra ice damage
        if status.status_type == StatusType.FREEZE and status.tick_damage > 0:
            tick_dmg = int(status.tick_damage)
            character.stats.hp = max(0, character.stats.hp - tick_dmg)
            events.append({
                "type": "freeze_tick",
                "name": status.name,
                "damage": tick_dmg,
                "emoji": "🧊",
                "target": character.name,
            })
            if character.stats.hp <= 0:
                character.is_alive = False

        # Decrement duration
        status.duration -= 1
        if status.duration <= 0:
            expired.append(status)

    # Remove expired
    for exp in expired:
        character.statuses.remove(exp)
        events.append({
            "type": "status_expired",
            "name": exp.name,
            "emoji": exp.emoji,
            "target": character.name,
        })

    return events


def get_active_modifiers(character: Character, stat_name: str) -> float:
    """Get total modifier for a stat from all active statuses."""
    total = 0.0
    for status in character.statuses:
        if stat_name in status.stat_modifiers:
            total += status.stat_modifiers[stat_name]
    return total


def has_taunt(character: Character) -> bool:
    """Check if character has an active taunt."""
    return character.has_status(StatusType.TAUNT)


def get_taunter(team: list[Character]) -> Optional[Character]:
    """Get the character with taunt in a team, if any."""
    for char in team:
        if char.is_alive and has_taunt(char):
            return char
    return None


def cleanse_debuffs(character: Character, count: int = 1) -> list[StatusEffect]:
    """Remove N debuff/negative statuses."""
    negative_types = (
        StatusType.DEBUFF, StatusType.DOT, StatusType.BLEED, StatusType.BURN,
        StatusType.POISON, StatusType.STUN, StatusType.SILENCE, StatusType.SLEEP,
        StatusType.PETRIFY, StatusType.FREEZE, StatusType.SHOCK, StatusType.CHARM,
        StatusType.IMMOBILIZE, StatusType.SLOW,
    )
    removed = []
    for s in list(character.statuses):
        if s.status_type in negative_types and len(removed) < count:
            character.statuses.remove(s)
            removed.append(s)
    return removed


# ──────────────────── Preset Status Factories ────────────────────

def make_burn(duration: int = 3, tick_damage: float = 15.0, chance: float = 40.0) -> StatusEffect:
    return StatusEffect(
        name="Podpalenie", status_type=StatusType.BURN, duration=duration,
        tick_damage=tick_damage, chance_to_apply=chance, emoji="🔥",
        element=Element.FIRE, description="Otrzymuje obrażenia od ognia co turę.",
    )

def make_bleed(duration: int = 3, tick_damage: float = 12.0, chance: float = 50.0) -> StatusEffect:
    return StatusEffect(
        name="Krwawienie", status_type=StatusType.BLEED, duration=duration,
        tick_damage=tick_damage, chance_to_apply=chance, emoji="🩸",
        stackable=True, max_stacks=3,
        description="Traci HP co turę. Kumuluje się.",
    )

def make_poison(duration: int = 4, tick_damage: float = 10.0, chance: float = 45.0) -> StatusEffect:
    return StatusEffect(
        name="Zatrucie", status_type=StatusType.POISON, duration=duration,
        tick_damage=tick_damage, chance_to_apply=chance, emoji="☠️",
        stackable=True, max_stacks=5,
        description="Trucizna zadaje obrażenia co turę.",
    )

def make_stun(duration: int = 1, chance: float = 30.0) -> StatusEffect:
    return StatusEffect(
        name="Ogłuszenie", status_type=StatusType.STUN, duration=duration,
        chance_to_apply=chance, emoji="💫",
        description="Nie może wykonywać akcji.",
    )

def make_freeze(duration: int = 1, tick_damage: float = 8.0, chance: float = 25.0) -> StatusEffect:
    return StatusEffect(
        name="Zamrożenie", status_type=StatusType.FREEZE, duration=duration,
        tick_damage=tick_damage, chance_to_apply=chance, emoji="🧊",
        element=Element.ICE,
        description="Zamrożony — nie może działać, otrzymuje obrażenia od lodu.",
    )

def make_shock(duration: int = 2, chance: float = 35.0) -> StatusEffect:
    return StatusEffect(
        name="Porażenie", status_type=StatusType.SHOCK, duration=duration,
        chance_to_apply=chance, emoji="⚡",
        element=Element.LIGHTNING,
        stat_modifiers={"spd": -0.3},
        description="Spowolniony, -30% szybkości.",
    )

def make_silence(duration: int = 2, chance: float = 30.0) -> StatusEffect:
    return StatusEffect(
        name="Uciszenie", status_type=StatusType.SILENCE, duration=duration,
        chance_to_apply=chance, emoji="🤐",
        description="Nie może używać zaklęć.",
    )

def make_sleep(duration: int = 2, chance: float = 20.0) -> StatusEffect:
    return StatusEffect(
        name="Sen", status_type=StatusType.SLEEP, duration=duration,
        chance_to_apply=chance, emoji="💤",
        description="Śpi — nie może działać, budzi się po otrzymaniu obrażeń.",
    )

def make_petrify(duration: int = 1, chance: float = 15.0) -> StatusEffect:
    return StatusEffect(
        name="Petryfikacja", status_type=StatusType.PETRIFY, duration=duration,
        chance_to_apply=chance, emoji="🗿",
        description="Zamieniony w kamień — nie może działać.",
    )

def make_charm(duration: int = 1, chance: float = 15.0) -> StatusEffect:
    return StatusEffect(
        name="Urok", status_type=StatusType.CHARM, duration=duration,
        chance_to_apply=chance, emoji="💕",
        description="Zauroczony — atakuje sojuszników.",
    )

def make_taunt(duration: int = 2) -> StatusEffect:
    return StatusEffect(
        name="Prowokacja", status_type=StatusType.TAUNT, duration=duration,
        chance_to_apply=100.0, emoji="🛡️",
        description="Wymusza ataki przeciwników na siebie.",
    )

def make_shield(amount: float = 100.0, duration: int = 3) -> StatusEffect:
    return StatusEffect(
        name="Tarcza", status_type=StatusType.SHIELD, duration=duration,
        shield_amount=amount, chance_to_apply=100.0, emoji="🛡️",
        description=f"Absorbuje {int(amount)} obrażeń.",
    )

def make_regen(duration: int = 3, tick_heal: float = 20.0) -> StatusEffect:
    return StatusEffect(
        name="Regeneracja", status_type=StatusType.REGEN, duration=duration,
        tick_heal=tick_heal, chance_to_apply=100.0, emoji="💚",
        description="Regeneruje HP co turę.",
    )

def make_lifesteal(duration: int = 3, power: float = 20.0) -> StatusEffect:
    return StatusEffect(
        name="Kradzież życia", status_type=StatusType.LIFESTEAL, duration=duration,
        power=power, chance_to_apply=100.0, emoji="🧛",
        description=f"Kradnie {int(power)}% zadanych obrażeń jako HP.",
    )

def make_reflect(duration: int = 2, power: float = 20.0) -> StatusEffect:
    return StatusEffect(
        name="Odbicie", status_type=StatusType.REFLECT, duration=duration,
        power=power, chance_to_apply=100.0, emoji="🪞",
        description=f"Odbija {int(power)}% obrażeń.",
    )

def make_haste(duration: int = 2, power: float = 0.3) -> StatusEffect:
    return StatusEffect(
        name="Przyspieszenie", status_type=StatusType.HASTE, duration=duration,
        stat_modifiers={"spd": power}, chance_to_apply=100.0, emoji="⚡",
        description=f"+{int(power*100)}% szybkości.",
    )

def make_slow(duration: int = 2, power: float = 0.3, chance: float = 40.0) -> StatusEffect:
    return StatusEffect(
        name="Spowolnienie", status_type=StatusType.SLOW, duration=duration,
        stat_modifiers={"spd": -power}, chance_to_apply=chance, emoji="🐌",
        description=f"-{int(power*100)}% szybkości.",
    )

def make_atk_buff(duration: int = 3, power: float = 0.25) -> StatusEffect:
    return StatusEffect(
        name="Wzmocnienie ATK", status_type=StatusType.BUFF, duration=duration,
        stat_modifiers={"atk": power}, chance_to_apply=100.0, emoji="⚔️",
        description=f"+{int(power*100)}% ATK.",
    )

def make_def_buff(duration: int = 3, power: float = 0.25) -> StatusEffect:
    return StatusEffect(
        name="Wzmocnienie DEF", status_type=StatusType.BUFF, duration=duration,
        stat_modifiers={"defense": power}, chance_to_apply=100.0, emoji="🛡️",
        description=f"+{int(power*100)}% DEF.",
    )

def make_matk_buff(duration: int = 3, power: float = 0.25) -> StatusEffect:
    return StatusEffect(
        name="Wzmocnienie MATK", status_type=StatusType.BUFF, duration=duration,
        stat_modifiers={"matk": power}, chance_to_apply=100.0, emoji="✨",
        description=f"+{int(power*100)}% MATK.",
    )

def make_def_debuff(duration: int = 3, power: float = 0.2, chance: float = 50.0) -> StatusEffect:
    return StatusEffect(
        name="Osłabienie DEF", status_type=StatusType.DEBUFF, duration=duration,
        stat_modifiers={"defense": -power}, chance_to_apply=chance, emoji="💔",
        description=f"-{int(power*100)}% DEF.",
    )

def make_immobilize(duration: int = 1, chance: float = 30.0) -> StatusEffect:
    return StatusEffect(
        name="Unieruchomienie", status_type=StatusType.IMMOBILIZE, duration=duration,
        chance_to_apply=chance, emoji="⛓️",
        description="Nie może się ruszać.",
    )
