"""
balance.py — Balance rules, stat caps, scaling limits.
"""

from __future__ import annotations

# ──────────────────── Stat Caps ────────────────────

MAX_CRIT_CHANCE: float = 75.0       # %
MAX_DODGE_CHANCE: float = 60.0      # %
MAX_RESISTANCE: float = 75.0        # %
MAX_LIFESTEAL: float = 40.0         # %
MAX_DAMAGE_REFLECT: float = 30.0    # %
MAX_SHIELD_PERCENT: float = 50.0    # % of max HP

# ──────────────────── Level / XP ────────────────────

MAX_LEVEL: int = 50
BASE_XP_PER_LEVEL: int = 100
XP_SCALING: float = 1.15            # XP needed = base * scaling^level

STAT_POINTS_PER_LEVEL: int = 3
BASE_HP: int = 500
HP_PER_POINT: int = 15
ATK_PER_POINT: int = 2
MATK_PER_POINT: int = 2
DEF_PER_POINT: int = 2
MDEF_PER_POINT: int = 2
SPD_PER_POINT: int = 1
LUCK_PER_POINT: int = 1

# ──────────────────── Activity Rewards ────────────────────

BASE_XP_PER_MESSAGE: int = 5
MAX_XP_PER_MESSAGE: int = 25
BASE_GOLD_PER_MESSAGE: int = 2
MAX_GOLD_PER_MESSAGE: int = 12
MESSAGE_COOLDOWN_SECONDS: int = 15   # anti-spam: min seconds between rewarded messages
MIN_MESSAGE_LENGTH: int = 8          # messages shorter than this get 0 XP
VOICE_XP_PER_MINUTE: int = 3
VOICE_GOLD_PER_MINUTE: int = 1
VOICE_REWARD_INTERVAL: int = 60     # seconds between voice rewards

# ──────────────────── Combat ────────────────────

MAX_TURNS: int = 100                 # prevent infinite battles
BASE_ACTION_COST: int = 100
SPEED_TO_TIMELINE: float = 2.0      # higher speed = faster timeline advance
COMBO_BONUS_DAMAGE: float = 0.25    # 25% extra damage per combo step
CHAIN_KILL_EXTRA_TURN_COST: int = 50 # reduced action cost on kill
CRIT_CHAIN_THRESHOLD: int = 3       # crits in a row to trigger chain bonus

# ──────────────────── Prestige ────────────────────

PRESTIGE_TIERS: dict[int, dict] = {
    1: {
        "min_level": 30,
        "xp_bonus": 0.15,
        "gold_per_msg_bonus": 2,
        "flat_hp": 30,
        "flat_atk": 5,
        "flat_matk": 5,
        "start_gold": 300,
        "emoji": "🥉",
        "color": 0xCD7F32,  # bronze
        "name": "Brązowy",
    },
    2: {
        "min_level": 35,
        "xp_bonus": 0.30,
        "gold_per_msg_bonus": 4,
        "flat_hp": 60,
        "flat_atk": 10,
        "flat_matk": 10,
        "start_gold": 600,
        "emoji": "🥈",
        "color": 0xC0C0C0,  # silver
        "name": "Srebrny",
    },
    3: {
        "min_level": 40,
        "xp_bonus": 0.45,
        "gold_per_msg_bonus": 6,
        "flat_hp": 90,
        "flat_atk": 15,
        "flat_matk": 15,
        "start_gold": 1000,
        "emoji": "🥇",
        "color": 0xFFD700,  # gold
        "name": "Złoty",
    },
    4: {
        "min_level": 45,
        "xp_bonus": 0.60,
        "gold_per_msg_bonus": 8,
        "flat_hp": 120,
        "flat_atk": 20,
        "flat_matk": 20,
        "start_gold": 1200,
        "emoji": "💎",
        "color": 0x00BFFF,  # diamond
        "name": "Diamentowy",
    },
    5: {
        "min_level": 50,
        "xp_bonus": 0.75,
        "gold_per_msg_bonus": 10,
        "flat_hp": 150,
        "flat_atk": 25,
        "flat_matk": 25,
        "start_gold": 1400,
        "emoji": "⭐",
        "color": 0xFF4500,  # star
        "name": "Legendarny",
    },
}

# For tiers > 5, scale linearly
def get_prestige_tier_data(tier: int) -> dict:
    """Get prestige tier data. For tiers > 5, scale from tier 5."""
    if tier <= 0:
        return {
            "min_level": 0, "xp_bonus": 0, "gold_per_msg_bonus": 0,
            "flat_hp": 0, "flat_atk": 0, "flat_matk": 0,
            "start_gold": 0, "emoji": "", "color": 0x808080, "name": "",
        }
    if tier in PRESTIGE_TIERS:
        return PRESTIGE_TIERS[tier]
    # Scale beyond tier 5
    base = PRESTIGE_TIERS[5]
    extra = tier - 5
    return {
        "min_level": base["min_level"] + extra * 5,
        "xp_bonus": min(base["xp_bonus"] + extra * 0.15, 2.0),  # cap at +200%
        "gold_per_msg_bonus": base["gold_per_msg_bonus"] + extra * 2,
        "flat_hp": base["flat_hp"] + extra * 30,
        "flat_atk": base["flat_atk"] + extra * 5,
        "flat_matk": base["flat_matk"] + extra * 5,
        "start_gold": base["start_gold"] + extra * 200,
        "emoji": "⭐",
        "color": 0xFF4500,
        "name": f"Legendarny +{extra}",
    }


def xp_for_level(level: int) -> int:
    """Calculate XP needed to reach a given level."""
    return int(BASE_XP_PER_LEVEL * (XP_SCALING ** (level - 1)))


def calculate_message_rewards(
    message_length: int,
    unique_words: int,
    prestige_tier: int = 0,
) -> tuple[int, int]:
    """
    Calculate XP and gold rewards for a message.

    Scoring:
    - Messages < MIN_MESSAGE_LENGTH chars: 0 XP, 0 gold
    - Base score = min(message_length / 10, 5) + min(unique_words / 3, 5)
    - XP = clamp(BASE_XP + score * 2, 0, MAX_XP)
    - Gold = clamp(BASE_GOLD + score, 0, MAX_GOLD)
    - Prestige bonuses applied after

    This rewards longer, more varied messages while capping gains.
    """
    if message_length < MIN_MESSAGE_LENGTH:
        return 0, 0

    length_score = min(message_length / 10.0, 5.0)
    word_score = min(unique_words / 3.0, 5.0)
    total_score = length_score + word_score

    xp = int(max(0, min(MAX_XP_PER_MESSAGE, BASE_XP_PER_MESSAGE + total_score * 2)))
    gold = int(max(0, min(MAX_GOLD_PER_MESSAGE, BASE_GOLD_PER_MESSAGE + total_score)))

    # Prestige bonuses
    tier_data = get_prestige_tier_data(prestige_tier)
    xp = int(xp * (1.0 + tier_data["xp_bonus"]))
    gold += tier_data["gold_per_msg_bonus"]

    return xp, gold
