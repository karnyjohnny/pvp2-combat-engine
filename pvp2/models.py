"""
models.py — Dataclasses for the PvP2 combat engine.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional


# ──────────────────── Enums ────────────────────


class Element(Enum):
    PHYSICAL = "physical"
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"
    DARK = "dark"
    HOLY = "holy"
    ARCANE = "arcane"
    NATURE = "nature"


class TargetType(Enum):
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"
    SINGLE_ALLY = "single_ally"
    ALL_ALLIES = "all_allies"
    SELF = "self"
    RANDOM_ENEMY = "random_enemy"


class ResourceType(Enum):
    MANA = "mana"
    RAGE = "rage"
    ENERGY = "energy"


class StatusType(Enum):
    BUFF = "buff"
    DEBUFF = "debuff"
    DOT = "dot"
    HOT = "hot"
    SHIELD = "shield"
    TAUNT = "taunt"
    STUN = "stun"
    IMMOBILIZE = "immobilize"
    SILENCE = "silence"
    SLEEP = "sleep"
    PETRIFY = "petrify"
    REGEN = "regen"
    LIFESTEAL = "lifesteal"
    REFLECT = "reflect"
    CHARM = "charm"
    BLEED = "bleed"
    BURN = "burn"
    FREEZE = "freeze"
    SHOCK = "shock"
    HASTE = "haste"
    SLOW = "slow"
    POISON = "poison"


class EventType(Enum):
    BEFORE_ATTACK = "before_attack"
    AFTER_ATTACK = "after_attack"
    ON_DAMAGE = "on_damage"
    ON_HEAL = "on_heal"
    ON_KILL = "on_kill"
    ON_DEATH = "on_death"
    ON_TURN_START = "on_turn_start"
    ON_TURN_END = "on_turn_end"
    ON_APPLY_STATUS = "on_apply_status"
    ON_REMOVE_STATUS = "on_remove_status"
    ON_CRIT = "on_crit"
    ON_DODGE = "on_dodge"
    ON_BLOCK = "on_block"
    ON_COMBO = "on_combo"


# ──────────────────── Stats ────────────────────


@dataclass
class Stats:
    """Core character stats."""
    hp: int = 500
    max_hp: int = 500
    atk: int = 30
    matk: int = 30
    defense: int = 15
    mdef: int = 15
    spd: int = 20
    luck: int = 10
    accuracy: int = 90
    evasion: int = 5
    crit_chance: float = 10.0   # %
    crit_dmg: float = 150.0     # % (1.5x)

    # Resource pools
    mana: int = 100
    max_mana: int = 100
    rage: int = 0
    max_rage: int = 100
    energy: int = 100
    max_energy: int = 100
    ultimate_charge: int = 0
    max_ultimate_charge: int = 100

    # Elemental resistances (% reduction)
    fire_res: float = 0.0
    ice_res: float = 0.0
    lightning_res: float = 0.0
    dark_res: float = 0.0
    holy_res: float = 0.0
    arcane_res: float = 0.0
    nature_res: float = 0.0

    def get_resistance(self, element: Element) -> float:
        """Get resistance for a given element."""
        res_map = {
            Element.FIRE: self.fire_res,
            Element.ICE: self.ice_res,
            Element.LIGHTNING: self.lightning_res,
            Element.DARK: self.dark_res,
            Element.HOLY: self.holy_res,
            Element.ARCANE: self.arcane_res,
            Element.NATURE: self.nature_res,
            Element.PHYSICAL: 0.0,
        }
        return res_map.get(element, 0.0)


# ──────────────────── Status Effect ────────────────────


@dataclass
class StatusEffect:
    """A status effect applied to a character."""
    name: str
    status_type: StatusType
    duration: int                  # turns remaining
    power: float = 0.0            # DOT/HOT tick damage/heal, buff/debuff %
    stat_modifiers: dict[str, float] = field(default_factory=dict)
    source_id: int = 0            # who applied it
    element: Element = Element.PHYSICAL
    stackable: bool = False
    max_stacks: int = 1
    current_stacks: int = 1
    tick_damage: float = 0.0      # per-turn damage (DOT)
    tick_heal: float = 0.0        # per-turn heal (HOT)
    shield_amount: float = 0.0    # remaining shield HP
    chance_to_apply: float = 100.0
    emoji: str = ""
    description: str = ""

    @property
    def is_cc(self) -> bool:
        """Check if this is a crowd control effect."""
        return self.status_type in (
            StatusType.STUN, StatusType.SILENCE, StatusType.SLEEP,
            StatusType.PETRIFY, StatusType.FREEZE, StatusType.CHARM,
            StatusType.IMMOBILIZE,
        )

    @property
    def prevents_action(self) -> bool:
        """Check if this status prevents any action."""
        return self.status_type in (
            StatusType.STUN, StatusType.SLEEP, StatusType.PETRIFY,
            StatusType.FREEZE, StatusType.CHARM,
        )

    @property
    def prevents_casting(self) -> bool:
        """Check if this prevents spell casting."""
        return self.status_type == StatusType.SILENCE or self.prevents_action


# ──────────────────── Skill Effect ────────────────────


@dataclass
class SkillEffect:
    """One effect within a skill (a skill can have multiple effects)."""
    effect_type: str              # "damage", "heal", "apply_status", "remove_status", "shield", "resource"
    power: float = 0.0           # base power / scaling factor
    element: Element = Element.PHYSICAL
    target: TargetType = TargetType.SINGLE_ENEMY
    scaling_stat: str = "atk"    # which stat this scales with
    scaling_ratio: float = 1.0   # multiplier for scaling stat
    status_to_apply: Optional[StatusEffect] = None
    chance: float = 100.0        # % chance this effect triggers
    description: str = ""


# ──────────────────── Skill ────────────────────


@dataclass
class Skill:
    """A combat skill / ability."""
    skill_id: str                  # unique identifier e.g. "fireball"
    name: str                      # display name e.g. "Kula Ognia"
    description: str
    emoji: str = "⚔️"
    element: Element = Element.PHYSICAL
    target_type: TargetType = TargetType.SINGLE_ENEMY
    effects: list[SkillEffect] = field(default_factory=list)
    cooldown: int = 0             # turns
    resource_type: ResourceType = ResourceType.MANA
    resource_cost: int = 0
    action_cost: int = 100        # timeline cost (higher = slower next turn)
    ultimate_charge_gain: int = 10
    is_ultimate: bool = False

    # Minimum stat requirements to use this skill
    min_atk: int = 0
    min_matk: int = 0
    min_defense: int = 0
    min_mdef: int = 0
    min_spd: int = 0
    min_luck: int = 0
    min_level: int = 1

    # Shop
    price: int = 100
    category: str = "Atak"

    def meets_requirements(self, stats: Stats, level: int = 1) -> bool:
        """Check if a character meets the stat requirements."""
        return (
            stats.atk >= self.min_atk
            and stats.matk >= self.min_matk
            and stats.defense >= self.min_defense
            and stats.mdef >= self.min_mdef
            and stats.spd >= self.min_spd
            and stats.luck >= self.min_luck
            and level >= self.min_level
        )


# ──────────────────── Passive Ability ────────────────────


@dataclass
class PassiveAbility:
    """A passive ability that listens to events."""
    name: str
    description: str
    event_type: EventType
    emoji: str = "🔮"
    # callback is set dynamically
    callback: Optional[Callable[..., Any]] = field(default=None, repr=False)


# ──────────────────── Character (in combat) ────────────────────


@dataclass
class Character:
    """Represents a character in combat."""
    user_id: int
    name: str
    team: int                      # 0 or 1
    stats: Stats = field(default_factory=Stats)
    level: int = 1
    prestige_tier: int = 0

    # Combat state
    is_alive: bool = True
    timeline_position: float = 0.0
    statuses: list[StatusEffect] = field(default_factory=list)
    cooldowns: dict[str, int] = field(default_factory=dict)  # skill_id -> turns remaining
    skills: list[Skill] = field(default_factory=list)
    passives: list[PassiveAbility] = field(default_factory=list)

    # Combo / chain tracking
    chain_counter: int = 0
    kills_this_turn: int = 0
    crits_this_turn: int = 0
    combo_element: Optional[Element] = None
    threat: float = 0.0

    def has_status(self, status_type: StatusType) -> bool:
        """Check if character has a specific status type."""
        return any(s.status_type == status_type for s in self.statuses)

    def get_statuses(self, status_type: StatusType) -> list[StatusEffect]:
        """Get all statuses of a specific type."""
        return [s for s in self.statuses if s.status_type == status_type]

    def can_act(self) -> bool:
        """Check if character can take an action this turn."""
        return self.is_alive and not any(s.prevents_action for s in self.statuses)

    def can_cast(self) -> bool:
        """Check if character can use spells."""
        return self.is_alive and not any(s.prevents_casting for s in self.statuses)

    def get_effective_stat(self, stat_name: str) -> float:
        """Get a stat value with all buff/debuff modifiers applied."""
        base = getattr(self.stats, stat_name, 0)
        if isinstance(base, (int, float)):
            modifier = 1.0
            flat_bonus = 0.0
            for status in self.statuses:
                if stat_name in status.stat_modifiers:
                    mod = status.stat_modifiers[stat_name]
                    if abs(mod) < 10:  # treat as multiplier
                        modifier += mod
                    else:  # treat as flat bonus
                        flat_bonus += mod
            return base * max(modifier, 0.1) + flat_bonus  # floor at 10% of base
        return base

    @property
    def effective_hp(self) -> float:
        """HP + shields."""
        shield_hp = sum(s.shield_amount for s in self.get_statuses(StatusType.SHIELD))
        return self.stats.hp + shield_hp


# ──────────────────── Battle State ────────────────────


@dataclass
class BattlePhase:
    """One phase/step of the battle for animation."""
    turn_number: int
    actor_name: str
    actor_emoji: str = "⚔️"
    action_name: str = ""
    target_names: list[str] = field(default_factory=list)
    description: str = ""
    damage_dealt: dict[str, int] = field(default_factory=dict)   # name -> damage
    healing_done: dict[str, int] = field(default_factory=dict)   # name -> heal
    statuses_applied: list[str] = field(default_factory=list)
    statuses_removed: list[str] = field(default_factory=list)
    kills: list[str] = field(default_factory=list)
    is_critical: bool = False
    is_dodge: bool = False
    is_combo: bool = False
    hp_bars: dict[str, tuple[int, int]] = field(default_factory=dict)  # name -> (current_hp, max_hp)
    extra_text: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class BattleResult:
    """Final result of a battle."""
    winning_team: int
    winners: list[Character] = field(default_factory=list)
    losers: list[Character] = field(default_factory=list)
    phases: list[BattlePhase] = field(default_factory=list)
    total_turns: int = 0
    total_damage: int = 0
    mvp: Optional[Character] = None
    duration_seconds: float = 0.0
