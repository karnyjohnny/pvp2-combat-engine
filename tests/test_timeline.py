"""Tests for the timeline-based turn system."""
import pytest
from pvp2.timeline import (
    initialize_timeline, get_next_actor, advance_timeline,
    grant_extra_turn, get_turn_order, normalize_timeline,
)
from pvp2.models import Character, Stats


def _make_char(name="Test", spd=20, **kwargs):
    return Character(
        user_id=hash(name) % 10000, name=name, team=0,
        stats=Stats(spd=spd, **kwargs),
    )


class TestInitializeTimeline:
    def test_faster_char_acts_first(self):
        fast = _make_char("Fast", spd=50)
        slow = _make_char("Slow", spd=10)
        ordered = initialize_timeline([slow, fast])
        assert ordered[0].name == "Fast"
        assert ordered[1].name == "Slow"

    def test_sets_positions(self):
        chars = [_make_char("A", spd=20), _make_char("B", spd=40)]
        initialize_timeline(chars)
        for c in chars:
            assert c.timeline_position > 0

    def test_equal_speed_both_get_same_position(self):
        a = _make_char("A", spd=30)
        b = _make_char("B", spd=30)
        initialize_timeline([a, b])
        assert a.timeline_position == b.timeline_position


class TestGetNextActor:
    def test_returns_lowest_position(self):
        a = _make_char("A")
        b = _make_char("B")
        a.timeline_position = 10.0
        b.timeline_position = 5.0
        assert get_next_actor([a, b]).name == "B"

    def test_skips_dead(self):
        a = _make_char("A")
        b = _make_char("B")
        a.timeline_position = 5.0
        a.is_alive = False
        b.timeline_position = 10.0
        assert get_next_actor([a, b]).name == "B"

    def test_none_if_all_dead(self):
        a = _make_char("A")
        a.is_alive = False
        assert get_next_actor([a]) is None


class TestAdvanceTimeline:
    def test_position_increases(self):
        c = _make_char("A", spd=20)
        c.timeline_position = 0.0
        new_pos = advance_timeline(c, action_cost=100)
        assert new_pos > 0.0

    def test_higher_speed_advances_less(self):
        fast = _make_char("Fast", spd=50)
        slow = _make_char("Slow", spd=10)
        fast.timeline_position = 0.0
        slow.timeline_position = 0.0
        fast_pos = advance_timeline(fast, 100)
        slow_pos = advance_timeline(slow, 100)
        assert fast_pos < slow_pos

    def test_higher_cost_advances_more(self):
        c = _make_char("A", spd=20)
        c.timeline_position = 0.0
        pos1 = advance_timeline(c, 50)
        c.timeline_position = 0.0
        pos2 = advance_timeline(c, 150)
        assert pos2 > pos1


class TestGrantExtraTurn:
    def test_reduces_position(self):
        c = _make_char("A", spd=20)
        c.timeline_position = 100.0
        grant_extra_turn(c, cost_reduction=50)
        assert c.timeline_position < 100.0

    def test_does_not_go_negative(self):
        c = _make_char("A", spd=20)
        c.timeline_position = 1.0
        grant_extra_turn(c, cost_reduction=5000)
        assert c.timeline_position >= 0.0


class TestGetTurnOrder:
    def test_returns_ordered(self):
        chars = [_make_char(f"C{i}", spd=10 + i * 5) for i in range(5)]
        initialize_timeline(chars)
        order = get_turn_order(chars, count=3)
        assert len(order) == 3
        assert order[0].timeline_position <= order[1].timeline_position

    def test_excludes_dead(self):
        a = _make_char("A", spd=50)
        b = _make_char("B", spd=10)
        a.is_alive = False
        initialize_timeline([a, b])
        order = get_turn_order([a, b])
        assert len(order) == 1
        assert order[0].name == "B"


class TestNormalizeTimeline:
    def test_normalizes_high_positions(self):
        chars = [_make_char("A"), _make_char("B")]
        chars[0].timeline_position = 500.0
        chars[1].timeline_position = 600.0
        normalize_timeline(chars)
        assert chars[0].timeline_position < 100.0

    def test_does_not_normalize_low_positions(self):
        chars = [_make_char("A"), _make_char("B")]
        chars[0].timeline_position = 10.0
        chars[1].timeline_position = 20.0
        normalize_timeline(chars)
        assert chars[0].timeline_position == 10.0
