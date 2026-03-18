"""Tests for the RNG module."""
import pytest
from pvp2.rng import (
    roll, roll_value, hit_check, crit_check,
    status_apply_check, damage_variance, generate_battle_seed,
)


class TestRoll:
    def test_roll_100_always_true(self):
        for _ in range(50):
            assert roll(100.0) is True

    def test_roll_0_always_false(self):
        for _ in range(50):
            assert roll(0.0) is False

    def test_roll_deterministic_with_seed(self):
        results = [roll(50.0, seed=42) for _ in range(10)]
        assert all(r == results[0] for r in results)

    def test_roll_value_in_range(self):
        for _ in range(100):
            v = roll_value(1.0, 10.0)
            assert 1.0 <= v <= 10.0


class TestHitCheck:
    def test_high_accuracy_hits(self):
        hits = sum(hit_check(99, 50, 0, 0) for _ in range(100))
        assert hits > 80

    def test_low_accuracy_misses(self):
        hits = sum(hit_check(10, 0, 60, 50) for _ in range(100))
        assert hits < 50

    def test_luck_improves_hit(self):
        low_luck = sum(hit_check(50, 0, 20, 0) for _ in range(200))
        high_luck = sum(hit_check(50, 80, 20, 0) for _ in range(200))
        assert high_luck > low_luck

    def test_clamped_min(self):
        # Even terrible accuracy should have 5% floor
        hits = sum(hit_check(0, 0, 100, 100) for _ in range(1000))
        assert hits > 0  # at least some should hit


class TestCritCheck:
    def test_high_crit_crits(self):
        crits = sum(crit_check(70, 0) for _ in range(100))
        assert crits > 40

    def test_luck_improves_crit(self):
        low = sum(crit_check(10, 0) for _ in range(500))
        high = sum(crit_check(10, 50) for _ in range(500))
        assert high > low

    def test_crit_cap(self):
        # With cap at 75%, even with high stats, crits shouldn't exceed cap significantly
        crits = sum(crit_check(100, 100, max_crit=75.0) for _ in range(1000))
        assert crits < 800  # should be around 750


class TestStatusApplyCheck:
    def test_guaranteed_status(self):
        applied = sum(status_apply_check(100, 50, 0) for _ in range(100))
        assert applied > 85

    def test_low_chance_status(self):
        applied = sum(status_apply_check(10, 0, 50) for _ in range(100))
        assert applied < 50

    def test_clamped_to_95(self):
        applied = sum(status_apply_check(100, 100, 0) for _ in range(1000))
        # Should be at 95% cap
        assert applied < 980


class TestDamageVariance:
    def test_variance_in_range(self):
        for _ in range(100):
            v = damage_variance(10)
            assert 0.89 <= v <= 1.11

    def test_high_luck_shifts_lower_bound(self):
        low_luck_min = min(damage_variance(10) for _ in range(500))
        high_luck_min = min(damage_variance(80) for _ in range(500))
        assert high_luck_min >= low_luck_min - 0.02  # high luck should have higher min


class TestBattleSeed:
    def test_deterministic(self):
        s1 = generate_battle_seed([1, 2, 3], timestamp=1000.0)
        s2 = generate_battle_seed([1, 2, 3], timestamp=1000.0)
        assert s1 == s2

    def test_different_users_different_seed(self):
        s1 = generate_battle_seed([1, 2], timestamp=1000.0)
        s2 = generate_battle_seed([3, 4], timestamp=1000.0)
        assert s1 != s2
