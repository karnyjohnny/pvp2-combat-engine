"""Tests for the prestige system."""
import pytest
import pytest_asyncio
import os
import tempfile

from pvp2.db import Database
from pvp2.balance import get_prestige_tier_data, PRESTIGE_TIERS


@pytest_asyncio.fixture
async def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    database = Database(db_path=db_path)
    await database.connect()
    yield database
    await database.close()
    os.unlink(db_path)


class TestPrestigeTierData:
    def test_tier_0_returns_zeros(self):
        data = get_prestige_tier_data(0)
        assert data["xp_bonus"] == 0
        assert data["flat_hp"] == 0

    def test_tier_1_data(self):
        data = get_prestige_tier_data(1)
        assert data["min_level"] == 30
        assert data["xp_bonus"] == 0.15
        assert data["flat_hp"] == 30
        assert data["start_gold"] == 300

    def test_tier_5_data(self):
        data = get_prestige_tier_data(5)
        assert data["min_level"] == 50
        assert data["emoji"] == "⭐"

    def test_tier_beyond_5_scales(self):
        data = get_prestige_tier_data(6)
        assert data["min_level"] > PRESTIGE_TIERS[5]["min_level"]
        assert data["flat_hp"] > PRESTIGE_TIERS[5]["flat_hp"]

    def test_each_tier_requires_higher_level(self):
        for i in range(1, 6):
            lower = get_prestige_tier_data(i)
            upper = get_prestige_tier_data(i + 1)
            assert upper["min_level"] > lower["min_level"]

    def test_bonuses_increase_with_tier(self):
        for i in range(1, 5):
            lower = get_prestige_tier_data(i)
            upper = get_prestige_tier_data(i + 1)
            assert upper["xp_bonus"] >= lower["xp_bonus"]
            assert upper["flat_hp"] >= lower["flat_hp"]
            assert upper["start_gold"] >= lower["start_gold"]


@pytest.mark.asyncio
class TestPrestigeDB:
    async def test_prestige_resets_level(self, db: Database):
        """Prestige should reset level to 1."""
        player = await db.get_or_create_player(1001, "TestPlayer")
        # Set level to 30 to qualify
        await db.update_player(1001, level=30)
        result = await db.prestige(1001)
        assert result["success"] is True
        assert result["new_tier"] == 1

        player = await db.get_or_create_player(1001)
        assert player["level"] == 1
        assert player["xp"] == 0

    async def test_prestige_resets_stats(self, db: Database):
        """Prestige should reset stats to base + prestige bonuses."""
        await db.get_or_create_player(1002, "TestPlayer")
        await db.update_player(1002, level=30, atk=80, matk=80, defense=50)
        result = await db.prestige(1002)
        assert result["success"] is True

        player = await db.get_or_create_player(1002)
        tier_data = get_prestige_tier_data(1)
        assert player["atk"] == 30 + tier_data["flat_atk"]  # base + prestige bonus
        assert player["defense"] == 15  # base, no prestige defense bonus

    async def test_prestige_resets_stat_points(self, db: Database):
        """Prestige should reset available stat points to 0."""
        await db.get_or_create_player(1003, "TestPlayer")
        await db.update_player(1003, level=30, available_stat_points=50)
        await db.prestige(1003)

        player = await db.get_or_create_player(1003)
        assert player["available_stat_points"] == 0

    async def test_prestige_clears_skills(self, db: Database):
        """Prestige should remove all skills."""
        await db.get_or_create_player(1004, "TestPlayer")
        await db.add_skill(1004, "fireball")
        await db.add_skill(1004, "ice_lance")
        await db.update_player(1004, level=30)

        skills_before = await db.get_player_skills(1004)
        assert len(skills_before) == 2

        await db.prestige(1004)

        skills_after = await db.get_player_skills(1004)
        assert len(skills_after) == 0

    async def test_prestige_clears_deck(self, db: Database):
        """Prestige should clear the deck."""
        await db.get_or_create_player(1005, "TestPlayer")
        await db.add_skill(1005, "fireball")
        await db.set_deck(1005, ["fireball"])
        await db.update_player(1005, level=30)

        await db.prestige(1005)

        deck = await db.get_deck(1005)
        assert all(slot is None for slot in deck)

    async def test_prestige_keeps_battle_stats(self, db: Database):
        """Prestige should keep total_battles and total_wins."""
        await db.get_or_create_player(1006, "TestPlayer")
        await db.update_player(1006, level=30, total_battles=50, total_wins=30)

        await db.prestige(1006)

        player = await db.get_or_create_player(1006)
        assert player["total_battles"] == 50
        assert player["total_wins"] == 30

    async def test_prestige_gives_start_gold(self, db: Database):
        """Prestige should give starting gold."""
        await db.get_or_create_player(1007, "TestPlayer")
        await db.update_player(1007, level=30, gold=5000)

        await db.prestige(1007)

        player = await db.get_or_create_player(1007)
        tier_data = get_prestige_tier_data(1)
        assert player["gold"] == tier_data["start_gold"]

    async def test_prestige_fails_below_level(self, db: Database):
        """Prestige should fail if below required level."""
        await db.get_or_create_player(1008, "TestPlayer")
        await db.update_player(1008, level=10)

        result = await db.prestige(1008)
        assert result["success"] is False
        assert result["required_level"] == 30

    async def test_second_prestige_requires_higher_level(self, db: Database):
        """Second prestige should require level 35."""
        await db.get_or_create_player(1009, "TestPlayer")
        await db.update_player(1009, level=30)
        await db.prestige(1009)

        # Now at tier 1, level 1. Need level 35 for tier 2.
        await db.update_player(1009, level=30)  # not enough for tier 2
        result = await db.prestige(1009)
        assert result["success"] is False
        assert result["required_level"] == 35

    async def test_prestige_bonuses_cumulative(self, db: Database):
        """Higher prestige tiers should give bigger flat stat bonuses."""
        await db.get_or_create_player(1010, "TestPlayer")
        await db.update_player(1010, level=30)
        await db.prestige(1010)  # tier 1

        player_t1 = await db.get_or_create_player(1010)
        hp_t1 = player_t1["max_hp"]

        await db.update_player(1010, level=35)
        await db.prestige(1010)  # tier 2

        player_t2 = await db.get_or_create_player(1010)
        hp_t2 = player_t2["max_hp"]

        assert hp_t2 > hp_t1  # tier 2 gives more HP bonus
