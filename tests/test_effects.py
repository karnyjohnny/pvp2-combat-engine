"""Tests for the effects module."""
import pytest
from pvp2.effects import (
    apply_status, remove_status, remove_statuses_by_type,
    tick_statuses, cleanse_debuffs, get_taunter,
    make_burn, make_bleed, make_stun, make_freeze, make_shield,
    make_regen, make_poison, make_silence, make_haste, make_taunt,
)
from pvp2.models import Character, Stats, StatusType


def _make_char(**kwargs):
    stats_kwargs = {"hp": 500, "max_hp": 500, "luck": 10}
    stats_kwargs.update(kwargs)
    return Character(
        user_id=1, name="Test", team=0,
        stats=Stats(**stats_kwargs),
    )


class TestApplyStatus:
    def test_apply_burn(self):
        char = _make_char()
        burn = make_burn(duration=3, tick_damage=15, chance=100.0)
        result = apply_status(char, burn, attacker_luck=50, target_luck=0)
        assert result is True
        assert char.has_status(StatusType.BURN)

    def test_refresh_non_stackable(self):
        char = _make_char()
        burn1 = make_burn(duration=2, chance=100.0)
        burn2 = make_burn(duration=5, chance=100.0)
        apply_status(char, burn1, attacker_luck=50, target_luck=0)
        apply_status(char, burn2, attacker_luck=50, target_luck=0)
        # Should only have one burn, refreshed to 5
        burns = char.get_statuses(StatusType.BURN)
        assert len(burns) == 1
        assert burns[0].duration == 5

    def test_stackable_bleed(self):
        char = _make_char()
        b1 = make_bleed(duration=3, tick_damage=10, chance=100.0)
        b2 = make_bleed(duration=3, tick_damage=10, chance=100.0)
        apply_status(char, b1, attacker_luck=50, target_luck=0)
        apply_status(char, b2, attacker_luck=50, target_luck=0)
        bleeds = char.get_statuses(StatusType.BLEED)
        assert len(bleeds) == 1
        assert bleeds[0].current_stacks == 2

    def test_hard_cc_no_stack(self):
        char = _make_char()
        stun = make_stun(duration=1, chance=100.0)
        freeze = make_freeze(duration=1, chance=100.0)
        apply_status(char, stun, attacker_luck=99)
        result = apply_status(char, freeze, attacker_luck=99)
        assert result is False  # can't stack hard CC

    def test_chance_based_application(self):
        char = _make_char()
        burn = make_burn(duration=3, tick_damage=15, chance=1.0)  # 1% chance
        applied = sum(
            apply_status(char, make_burn(duration=3, tick_damage=15, chance=1.0), attacker_luck=0, target_luck=50)
            for _ in range(100)
        )
        # With 1% chance and bad luck, very few should apply
        assert applied < 30


class TestRemoveStatus:
    def test_remove_by_name(self):
        char = _make_char()
        apply_status(char, make_burn(chance=100.0), attacker_luck=50)
        removed = remove_status(char, "Podpalenie")
        assert removed is not None
        assert not char.has_status(StatusType.BURN)

    def test_remove_nonexistent(self):
        char = _make_char()
        removed = remove_status(char, "Nieistniejący")
        assert removed is None

    def test_remove_by_type(self):
        char = _make_char()
        apply_status(char, make_burn(chance=100.0), attacker_luck=50)
        apply_status(char, make_poison(chance=100.0), attacker_luck=50)
        removed = remove_statuses_by_type(char, StatusType.BURN)
        assert len(removed) == 1
        assert char.has_status(StatusType.POISON)


class TestTickStatuses:
    def test_dot_tick_deals_damage(self):
        char = _make_char(hp=500)
        apply_status(char, make_burn(duration=3, tick_damage=20, chance=100.0), attacker_luck=50)
        events = tick_statuses(char)
        dot_events = [e for e in events if e["type"] == "dot_tick"]
        assert len(dot_events) == 1
        assert char.stats.hp < 500

    def test_hot_tick_heals(self):
        char = _make_char(hp=400, max_hp=500)
        apply_status(char, make_regen(duration=3, tick_heal=25))
        events = tick_statuses(char)
        hot_events = [e for e in events if e["type"] == "hot_tick"]
        assert len(hot_events) == 1
        assert char.stats.hp > 400

    def test_duration_decrements(self):
        char = _make_char()
        apply_status(char, make_haste(duration=2))
        tick_statuses(char)
        assert char.statuses[0].duration == 1
        tick_statuses(char)
        assert not char.has_status(StatusType.HASTE)

    def test_expired_status_removed(self):
        char = _make_char()
        apply_status(char, make_haste(duration=1))
        events = tick_statuses(char)
        expired = [e for e in events if e["type"] == "status_expired"]
        assert len(expired) == 1
        assert len(char.statuses) == 0

    def test_dot_can_kill(self):
        char = _make_char(hp=5)
        apply_status(char, make_burn(duration=3, tick_damage=20, chance=100.0), attacker_luck=50)
        tick_statuses(char)
        assert char.stats.hp <= 0
        assert char.is_alive is False


class TestCleanse:
    def test_cleanse_removes_debuffs(self):
        char = _make_char()
        apply_status(char, make_burn(chance=100.0), attacker_luck=50)
        apply_status(char, make_poison(chance=100.0), attacker_luck=50)
        apply_status(char, make_haste())  # buff, should not be removed
        removed = cleanse_debuffs(char, count=2)
        assert len(removed) == 2
        assert char.has_status(StatusType.HASTE)

    def test_cleanse_respects_count(self):
        char = _make_char()
        apply_status(char, make_burn(chance=100.0), attacker_luck=50)
        apply_status(char, make_poison(chance=100.0), attacker_luck=50)
        apply_status(char, make_silence(chance=100.0), attacker_luck=50)
        removed = cleanse_debuffs(char, count=1)
        assert len(removed) == 1
        assert len(char.statuses) == 2


class TestTaunt:
    def test_get_taunter(self):
        chars = [_make_char(), _make_char(), _make_char()]
        apply_status(chars[1], make_taunt(duration=2))
        taunter = get_taunter(chars)
        assert taunter is chars[1]

    def test_no_taunter(self):
        chars = [_make_char(), _make_char()]
        taunter = get_taunter(chars)
        assert taunter is None
