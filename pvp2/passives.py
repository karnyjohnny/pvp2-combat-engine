"""
passives.py — Passive abilities as event listeners.

Passives are declared as functions that register on the EventBus.
Each passive listens to specific events and modifies combat behavior.
"""

from __future__ import annotations

from pvp2.events import EventBus
from pvp2.models import Character, EventType, PassiveAbility


def register_passive(
    event_bus: EventBus,
    character: Character,
    passive: PassiveAbility,
) -> None:
    """Register a passive ability on the event bus."""
    if passive.callback:
        event_bus.subscribe(passive.event_type, passive.callback)


def register_all_passives(
    event_bus: EventBus,
    character: Character,
) -> None:
    """Register all passives for a character."""
    for passive in character.passives:
        register_passive(event_bus, character, passive)


# ──────────────────── Built-in Passives ────────────────────


def make_thorns_passive(character: Character, reflect_pct: float = 10.0) -> PassiveAbility:
    """Thorns: reflect a percentage of damage taken."""
    async def on_damage(target: Character, attacker: Character, damage: int, **kw):
        if target.user_id == character.user_id and attacker.user_id != character.user_id:
            reflected = int(damage * reflect_pct / 100.0)
            if reflected > 0:
                attacker.stats.hp = max(0, attacker.stats.hp - reflected)
                if attacker.stats.hp <= 0:
                    attacker.is_alive = False
                return {"reflected_damage": reflected, "thorns_source": character.name}
    return PassiveAbility(
        name="Ciernie",
        description=f"Odbija {int(reflect_pct)}% otrzymanych obrażeń.",
        event_type=EventType.ON_DAMAGE,
        emoji="🌵",
        callback=on_damage,
    )


def make_berserker_passive(character: Character, threshold: float = 30.0) -> PassiveAbility:
    """Berserker: +25% ATK when HP below threshold%."""
    async def on_turn_start(actor: Character, **kw):
        if actor.user_id == character.user_id:
            hp_pct = (actor.stats.hp / actor.stats.max_hp) * 100
            if hp_pct <= threshold:
                return {"berserker_active": True, "atk_bonus": 0.25}
    return PassiveAbility(
        name="Berserker",
        description=f"Poniżej {int(threshold)}% HP: +25% ATK.",
        event_type=EventType.ON_TURN_START,
        emoji="🔴",
        callback=on_turn_start,
    )


def make_executioner_passive(character: Character, threshold: float = 25.0) -> PassiveAbility:
    """Executioner: +30% damage to targets below threshold% HP."""
    async def before_attack(attacker: Character, target: Character, **kw):
        if attacker.user_id == character.user_id:
            hp_pct = (target.stats.hp / target.stats.max_hp) * 100
            if hp_pct <= threshold:
                return {"damage_bonus": 0.30}
    return PassiveAbility(
        name="Egzekutor",
        description=f"+30% obrażeń przeciw celom poniżej {int(threshold)}% HP.",
        event_type=EventType.BEFORE_ATTACK,
        emoji="⚰️",
        callback=before_attack,
    )


def make_second_wind_passive(character: Character) -> PassiveAbility:
    """Second Wind: heal 15% max HP on first kill."""
    triggered = {"done": False}

    async def on_kill(killer: Character, victim: Character, **kw):
        if killer.user_id == character.user_id and not triggered["done"]:
            triggered["done"] = True
            heal = int(killer.stats.max_hp * 0.15)
            killer.stats.hp = min(killer.stats.max_hp, killer.stats.hp + heal)
            return {"second_wind_heal": heal}
    return PassiveAbility(
        name="Drugi Oddech",
        description="Pierwsze zabójstwo leczy 15% maks. HP.",
        event_type=EventType.ON_KILL,
        emoji="💨",
        callback=on_kill,
    )


def make_vampiric_passive(character: Character, pct: float = 10.0) -> PassiveAbility:
    """Vampiric: heal for % of damage dealt."""
    async def after_attack(attacker: Character, damage: int, **kw):
        if attacker.user_id == character.user_id and damage > 0:
            heal = int(damage * pct / 100.0)
            attacker.stats.hp = min(attacker.stats.max_hp, attacker.stats.hp + heal)
            return {"vampiric_heal": heal}
    return PassiveAbility(
        name="Wampiryzm",
        description=f"Leczy {int(pct)}% zadanych obrażeń.",
        event_type=EventType.AFTER_ATTACK,
        emoji="🧛",
        callback=after_attack,
    )


def make_lucky_dodge_passive(character: Character) -> PassiveAbility:
    """Lucky Dodge: on dodge, gain +10% crit chance for 1 turn."""
    async def on_dodge(dodger: Character, **kw):
        if dodger.user_id == character.user_id:
            return {"crit_bonus": 10.0}
    return PassiveAbility(
        name="Szczęśliwy Unik",
        description="Po uniku: +10% szansy na krytyk na 1 turę.",
        event_type=EventType.ON_DODGE,
        emoji="🍀",
        callback=on_dodge,
    )
