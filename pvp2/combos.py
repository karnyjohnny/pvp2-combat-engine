"""
combos.py — Combo / Chain / Ultimate mechanics.

Element combos:
    Fire + Ice = "Parowanie" (Steam) — AoE damage
    Fire + Lightning = "Plazma" — bonus damage + stun
    Ice + Lightning = "Superprzewodnik" — defense shred
    Dark + Holy = "Równowaga" — heal + damage
    Lightning + Ice = "Zamieć Elektryczna" — AoE slow

Chain mechanics:
    - Kill → extra turn (reduced action cost)
    - Crit → increment chain counter → at threshold, bonus damage
    - Consecutive same-element hits → element combo bonus

Ultimate charge:
    - Gained on: dealing damage, taking damage, killing, healing
    - Spent: use ultimate skill (requires full charge)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pvp2 import balance
from pvp2.models import Character, Element


@dataclass
class ComboResult:
    """Result of a combo check."""
    triggered: bool = False
    combo_name: str = ""
    combo_emoji: str = ""
    bonus_damage: float = 0.0
    bonus_effect: str = ""
    description: str = ""


# Element combo table: (elem1, elem2) -> combo data
ELEMENT_COMBOS: dict[frozenset[Element], dict] = {
    frozenset({Element.FIRE, Element.ICE}): {
        "name": "Parowanie",
        "emoji": "♨️",
        "bonus_damage": 0.3,
        "effect": "aoe_damage",
        "description": "Ogień i lód zderzają się — fala pary zadaje obrażenia!",
    },
    frozenset({Element.FIRE, Element.LIGHTNING}): {
        "name": "Plazma",
        "emoji": "🌩️",
        "bonus_damage": 0.4,
        "effect": "stun",
        "description": "Ogień i błyskawice tworzą plazmę — ogłuszenie!",
    },
    frozenset({Element.ICE, Element.LIGHTNING}): {
        "name": "Superprzewodnik",
        "emoji": "❄️⚡",
        "bonus_damage": 0.2,
        "effect": "defense_shred",
        "description": "Lód i prąd — obrona przeciwnika spada!",
    },
    frozenset({Element.DARK, Element.HOLY}): {
        "name": "Równowaga",
        "emoji": "☯️",
        "bonus_damage": 0.25,
        "effect": "heal_and_damage",
        "description": "Mrok i światło w równowadze — leczy i rani!",
    },
    frozenset({Element.FIRE, Element.NATURE}): {
        "name": "Pożar",
        "emoji": "🌿🔥",
        "bonus_damage": 0.35,
        "effect": "dot",
        "description": "Natura płonie — potężny ogień trawi wszystko!",
    },
    frozenset({Element.NATURE, Element.ICE}): {
        "name": "Wieczna Zima",
        "emoji": "🌨️",
        "bonus_damage": 0.2,
        "effect": "slow",
        "description": "Natura zamiera w lodzie — spowolnienie!",
    },
    frozenset({Element.DARK, Element.LIGHTNING}): {
        "name": "Mroczny Piorun",
        "emoji": "⚡💀",
        "bonus_damage": 0.35,
        "effect": "silence",
        "description": "Mroczna energia piorunuje — uciszenie!",
    },
    frozenset({Element.HOLY, Element.NATURE}): {
        "name": "Błogosławieństwo Natury",
        "emoji": "🌿✨",
        "bonus_damage": 0.15,
        "effect": "regen",
        "description": "Święta moc natury — regeneracja!",
    },
}


def check_element_combo(
    current_element: Element,
    previous_element: Optional[Element],
) -> ComboResult:
    """
    Check if two consecutive elements create a combo.
    """
    if previous_element is None or current_element == previous_element:
        return ComboResult()

    if current_element == Element.PHYSICAL or previous_element == Element.PHYSICAL:
        return ComboResult()

    key = frozenset({current_element, previous_element})
    combo_data = ELEMENT_COMBOS.get(key)

    if combo_data:
        return ComboResult(
            triggered=True,
            combo_name=combo_data["name"],
            combo_emoji=combo_data["emoji"],
            bonus_damage=combo_data["bonus_damage"],
            bonus_effect=combo_data["effect"],
            description=combo_data["description"],
        )
    return ComboResult()


def process_chain_counter(character: Character, is_crit: bool) -> float:
    """
    Process crit chain counter.
    Returns bonus damage multiplier if chain threshold reached.
    """
    if is_crit:
        character.crits_this_turn += 1
        if character.crits_this_turn >= balance.CRIT_CHAIN_THRESHOLD:
            character.crits_this_turn = 0
            return balance.COMBO_BONUS_DAMAGE
    else:
        character.crits_this_turn = 0
    return 0.0


def process_kill_chain(character: Character) -> bool:
    """
    Process kill → extra turn mechanic.
    Returns True if extra turn should be granted.
    """
    character.kills_this_turn += 1
    return character.kills_this_turn > 0  # first kill grants extra turn


def reset_turn_counters(character: Character) -> None:
    """Reset per-turn combo/chain counters."""
    character.kills_this_turn = 0
    character.combo_element = None


def calculate_combo_bonus(character: Character) -> float:
    """Calculate total combo damage bonus from chain counter."""
    return character.chain_counter * balance.COMBO_BONUS_DAMAGE


def update_threat(character: Character, damage_dealt: int, healing_done: int) -> None:
    """Update threat score based on actions."""
    character.threat += damage_dealt * 1.0
    character.threat += healing_done * 1.5  # healing generates more threat
