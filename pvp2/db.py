"""
db.py — Async SQLite database module.

Auto-creates players on first mention (no registration needed).
Uses aiosqlite for async operations.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import aiosqlite

DB_PATH = os.path.join(os.path.dirname(__file__), "pvp2.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    user_id         INTEGER PRIMARY KEY,
    name            TEXT NOT NULL DEFAULT 'Wojownik',
    level           INTEGER NOT NULL DEFAULT 1,
    xp              INTEGER NOT NULL DEFAULT 0,
    gold            INTEGER NOT NULL DEFAULT 0,

    -- Core stats (allocatable)
    hp              INTEGER NOT NULL DEFAULT 500,
    max_hp          INTEGER NOT NULL DEFAULT 500,
    atk             INTEGER NOT NULL DEFAULT 30,
    matk            INTEGER NOT NULL DEFAULT 30,
    defense         INTEGER NOT NULL DEFAULT 15,
    mdef            INTEGER NOT NULL DEFAULT 15,
    spd             INTEGER NOT NULL DEFAULT 20,
    luck            INTEGER NOT NULL DEFAULT 10,
    accuracy        INTEGER NOT NULL DEFAULT 90,
    evasion         INTEGER NOT NULL DEFAULT 5,
    crit_chance     REAL NOT NULL DEFAULT 10.0,
    crit_dmg        REAL NOT NULL DEFAULT 150.0,

    -- Resources
    mana            INTEGER NOT NULL DEFAULT 100,
    max_mana        INTEGER NOT NULL DEFAULT 100,
    rage            INTEGER NOT NULL DEFAULT 0,
    max_rage        INTEGER NOT NULL DEFAULT 100,
    energy          INTEGER NOT NULL DEFAULT 100,
    max_energy      INTEGER NOT NULL DEFAULT 100,
    ultimate_charge INTEGER NOT NULL DEFAULT 0,

    -- Stat points
    available_stat_points INTEGER NOT NULL DEFAULT 0,

    -- Prestige
    prestige_tier   INTEGER NOT NULL DEFAULT 0,
    prestige_flat_hp    INTEGER NOT NULL DEFAULT 0,
    prestige_flat_atk   INTEGER NOT NULL DEFAULT 0,
    prestige_flat_matk  INTEGER NOT NULL DEFAULT 0,

    -- Battle stats
    total_battles   INTEGER NOT NULL DEFAULT 0,
    total_wins      INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    created_at      REAL NOT NULL DEFAULT 0,
    last_active     REAL NOT NULL DEFAULT 0,
    last_message_reward REAL NOT NULL DEFAULT 0,
    last_voice_reward   REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_skills (
    user_id     INTEGER NOT NULL,
    skill_id    TEXT NOT NULL,
    purchased_at REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id) REFERENCES players(user_id)
);

CREATE TABLE IF NOT EXISTS player_deck (
    user_id     INTEGER NOT NULL,
    slot        INTEGER NOT NULL CHECK(slot >= 1 AND slot <= 5),
    skill_id    TEXT NOT NULL,
    PRIMARY KEY (user_id, slot),
    FOREIGN KEY (user_id) REFERENCES players(user_id)
);

CREATE TABLE IF NOT EXISTS battle_history (
    battle_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL NOT NULL,
    guild_id        INTEGER NOT NULL DEFAULT 0,
    team1_ids       TEXT NOT NULL DEFAULT '',
    team2_ids       TEXT NOT NULL DEFAULT '',
    winner_team     INTEGER NOT NULL DEFAULT 0,
    total_turns     INTEGER NOT NULL DEFAULT 0,
    mvp_id          INTEGER NOT NULL DEFAULT 0,
    log_summary     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS activity_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    guild_id        INTEGER NOT NULL DEFAULT 0,
    channel_id      INTEGER NOT NULL DEFAULT 0,
    message_length  INTEGER NOT NULL DEFAULT 0,
    unique_words    INTEGER NOT NULL DEFAULT 0,
    xp_awarded      INTEGER NOT NULL DEFAULT 0,
    gold_awarded    INTEGER NOT NULL DEFAULT 0,
    reward_type     TEXT NOT NULL DEFAULT 'message',
    timestamp       REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES players(user_id)
);
"""


class Database:
    """Async SQLite database wrapper for PvP2."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Connect to the database and create tables."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    # ──────────────────── Player CRUD ────────────────────

    async def get_or_create_player(self, user_id: int, name: str = "Wojownik") -> dict[str, Any]:
        """
        Get a player by user_id. If not found, create automatically.
        This is the core auto-registration mechanism.
        """
        async with self.db.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        # Auto-create
        now = time.time()
        await self.db.execute(
            """INSERT INTO players (user_id, name, created_at, last_active)
               VALUES (?, ?, ?, ?)""",
            (user_id, name, now, now),
        )
        await self.db.commit()

        async with self.db.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row)  # type: ignore

    async def update_player(self, user_id: int, **kwargs: Any) -> None:
        """Update player fields."""
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [user_id]
        await self.db.execute(
            f"UPDATE players SET {sets} WHERE user_id = ?", values
        )
        await self.db.commit()

    async def add_xp(self, user_id: int, xp: int) -> dict[str, Any]:
        """
        Add XP to a player. Returns dict with level_up info.
        """
        from pvp2.balance import STAT_POINTS_PER_LEVEL, xp_for_level, MAX_LEVEL

        player = await self.get_or_create_player(user_id)
        new_xp = player["xp"] + xp
        new_level = player["level"]
        stat_points_gained = 0
        levels_gained = 0

        while new_level < MAX_LEVEL:
            needed = xp_for_level(new_level + 1)
            if new_xp >= needed:
                new_xp -= needed
                new_level += 1
                levels_gained += 1
                stat_points_gained += STAT_POINTS_PER_LEVEL
            else:
                break

        await self.update_player(
            user_id,
            xp=new_xp,
            level=new_level,
            available_stat_points=player["available_stat_points"] + stat_points_gained,
            last_active=time.time(),
        )

        return {
            "old_level": player["level"],
            "new_level": new_level,
            "levels_gained": levels_gained,
            "stat_points_gained": stat_points_gained,
            "current_xp": new_xp,
            "xp_needed": xp_for_level(new_level + 1) if new_level < MAX_LEVEL else 0,
        }

    async def add_gold(self, user_id: int, amount: int) -> int:
        """Add gold to a player. Returns new total."""
        player = await self.get_or_create_player(user_id)
        new_gold = max(0, player["gold"] + amount)
        await self.update_player(user_id, gold=new_gold)
        return new_gold

    async def allocate_stat(self, user_id: int, stat_name: str, points: int = 1) -> bool:
        """
        Allocate stat points. Returns True if successful.
        """
        from pvp2.balance import (
            HP_PER_POINT, ATK_PER_POINT, MATK_PER_POINT,
            DEF_PER_POINT, MDEF_PER_POINT, SPD_PER_POINT, LUCK_PER_POINT,
        )

        valid_stats = {
            "hp": ("max_hp", HP_PER_POINT),
            "atk": ("atk", ATK_PER_POINT),
            "matk": ("matk", MATK_PER_POINT),
            "defense": ("defense", DEF_PER_POINT),
            "mdef": ("mdef", MDEF_PER_POINT),
            "spd": ("spd", SPD_PER_POINT),
            "luck": ("luck", LUCK_PER_POINT),
        }

        if stat_name not in valid_stats:
            return False

        player = await self.get_or_create_player(user_id)
        if player["available_stat_points"] < points:
            return False

        db_field, per_point = valid_stats[stat_name]
        increase = per_point * points
        new_value = player[db_field] + increase

        updates: dict[str, Any] = {
            db_field: new_value,
            "available_stat_points": player["available_stat_points"] - points,
        }

        # HP allocation also increases current HP
        if stat_name == "hp":
            updates["hp"] = player["hp"] + increase

        await self.update_player(user_id, **updates)
        return True

    # ──────────────────── Skills ────────────────────

    async def get_player_skills(self, user_id: int) -> list[str]:
        """Get all skill IDs owned by a player."""
        await self.get_or_create_player(user_id)
        async with self.db.execute(
            "SELECT skill_id FROM player_skills WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row["skill_id"] for row in rows]

    async def add_skill(self, user_id: int, skill_id: str) -> bool:
        """Add a skill to player's collection. Returns False if already owned."""
        existing = await self.get_player_skills(user_id)
        if skill_id in existing:
            return False
        await self.db.execute(
            "INSERT INTO player_skills (user_id, skill_id, purchased_at) VALUES (?, ?, ?)",
            (user_id, skill_id, time.time()),
        )
        await self.db.commit()
        return True

    async def remove_skill(self, user_id: int, skill_id: str) -> bool:
        """Remove a skill from player's collection."""
        result = await self.db.execute(
            "DELETE FROM player_skills WHERE user_id = ? AND skill_id = ?",
            (user_id, skill_id),
        )
        await self.db.commit()
        return result.rowcount > 0

    async def remove_all_skills(self, user_id: int) -> int:
        """Remove all skills from a player. Returns count removed."""
        result = await self.db.execute(
            "DELETE FROM player_skills WHERE user_id = ?", (user_id,)
        )
        await self.db.commit()
        return result.rowcount

    # ──────────────────── Deck ────────────────────

    async def get_deck(self, user_id: int) -> list[Optional[str]]:
        """Get player's deck (5 slots). Returns list of skill_ids (None for empty)."""
        await self.get_or_create_player(user_id)
        deck: list[Optional[str]] = [None] * 5
        async with self.db.execute(
            "SELECT slot, skill_id FROM player_deck WHERE user_id = ? ORDER BY slot",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                deck[row["slot"] - 1] = row["skill_id"]
        return deck

    async def set_deck(self, user_id: int, skill_ids: list[str]) -> None:
        """Set player's deck (up to 5 skills)."""
        await self.db.execute("DELETE FROM player_deck WHERE user_id = ?", (user_id,))
        for i, sid in enumerate(skill_ids[:5]):
            if sid:
                await self.db.execute(
                    "INSERT INTO player_deck (user_id, slot, skill_id) VALUES (?, ?, ?)",
                    (user_id, i + 1, sid),
                )
        await self.db.commit()

    async def clear_deck(self, user_id: int) -> None:
        """Clear all deck slots."""
        await self.db.execute("DELETE FROM player_deck WHERE user_id = ?", (user_id,))
        await self.db.commit()

    # ──────────────────── Activity Tracking ────────────────────

    async def can_reward_message(self, user_id: int) -> bool:
        """Check if enough time has passed since last message reward."""
        from pvp2.balance import MESSAGE_COOLDOWN_SECONDS
        player = await self.get_or_create_player(user_id)
        return (time.time() - player["last_message_reward"]) >= MESSAGE_COOLDOWN_SECONDS

    async def record_message_reward(
        self, user_id: int, guild_id: int, channel_id: int,
        msg_length: int, unique_words: int, xp: int, gold: int,
    ) -> None:
        """Record a message activity reward."""
        await self.db.execute(
            """INSERT INTO activity_log
               (user_id, guild_id, channel_id, message_length, unique_words,
                xp_awarded, gold_awarded, reward_type, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'message', ?)""",
            (user_id, guild_id, channel_id, msg_length, unique_words, xp, gold, time.time()),
        )
        await self.update_player(user_id, last_message_reward=time.time())
        await self.db.commit()

    async def record_voice_reward(self, user_id: int, guild_id: int, xp: int, gold: int) -> None:
        """Record a voice channel activity reward."""
        await self.db.execute(
            """INSERT INTO activity_log
               (user_id, guild_id, channel_id, message_length, unique_words,
                xp_awarded, gold_awarded, reward_type, timestamp)
               VALUES (?, ?, 0, 0, 0, ?, ?, 'voice', ?)""",
            (user_id, guild_id, xp, gold, time.time()),
        )
        await self.update_player(user_id, last_voice_reward=time.time())
        await self.db.commit()

    # ──────────────────── Battle History ────────────────────

    async def record_battle(
        self, guild_id: int, team1_ids: list[int], team2_ids: list[int],
        winner_team: int, total_turns: int, mvp_id: int, log_summary: str,
    ) -> int:
        """Record a battle. Returns battle_id."""
        cursor = await self.db.execute(
            """INSERT INTO battle_history
               (timestamp, guild_id, team1_ids, team2_ids, winner_team,
                total_turns, mvp_id, log_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                time.time(), guild_id,
                ",".join(str(i) for i in team1_ids),
                ",".join(str(i) for i in team2_ids),
                winner_team, total_turns, mvp_id, log_summary,
            ),
        )
        await self.db.commit()
        return cursor.lastrowid or 0

    async def get_player_battles(self, user_id: int, limit: int = 10) -> list[dict]:
        """Get recent battles involving a player."""
        async with self.db.execute(
            """SELECT * FROM battle_history
               WHERE team1_ids LIKE ? OR team2_ids LIKE ?
               ORDER BY timestamp DESC LIMIT ?""",
            (f"%{user_id}%", f"%{user_id}%", limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ──────────────────── Prestige ────────────────────

    async def prestige(self, user_id: int) -> dict[str, Any]:
        """
        Perform prestige reset. Returns prestige info.
        Resets: level, xp, stats, stat points, skills, deck
        Keeps: total_battles, total_wins, prestige_tier
        Gives: starting gold, permanent bonuses
        """
        from pvp2.balance import get_prestige_tier_data

        player = await self.get_or_create_player(user_id)
        new_tier = player["prestige_tier"] + 1
        tier_data = get_prestige_tier_data(new_tier)

        # Check if player meets level requirement
        if player["level"] < tier_data["min_level"]:
            return {"success": False, "required_level": tier_data["min_level"]}

        # Reset player to base stats with prestige bonuses
        await self.update_player(
            user_id,
            level=1,
            xp=0,
            gold=tier_data["start_gold"],
            hp=500 + tier_data["flat_hp"],
            max_hp=500 + tier_data["flat_hp"],
            atk=30 + tier_data["flat_atk"],
            matk=30 + tier_data["flat_matk"],
            defense=15,
            mdef=15,
            spd=20,
            luck=10,
            accuracy=90,
            evasion=5,
            crit_chance=10.0,
            crit_dmg=150.0,
            mana=100,
            max_mana=100,
            rage=0,
            energy=100,
            max_energy=100,
            ultimate_charge=0,
            available_stat_points=0,
            prestige_tier=new_tier,
            prestige_flat_hp=tier_data["flat_hp"],
            prestige_flat_atk=tier_data["flat_atk"],
            prestige_flat_matk=tier_data["flat_matk"],
        )

        # Clear skills and deck
        await self.remove_all_skills(user_id)
        await self.clear_deck(user_id)

        return {
            "success": True,
            "new_tier": new_tier,
            "tier_data": tier_data,
            "start_gold": tier_data["start_gold"],
        }


# Singleton
_db_instance: Optional[Database] = None


async def get_db() -> Database:
    """Get or create the database singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        await _db_instance.connect()
    return _db_instance
