"""Tests for the damage module."""
import pytest
from pvp2.damage import calculate_damage, calculate_healing, apply_damage, apply_healing
from pvp2.models import Character, Element, SkillEffect, Stats, StatusType, StatusEffect


def _make_char(team=0, **kwargs):
    stats_kwargs = {
        "hp": 500, "max_hp": 500, "atk": 50, "matk": 50,
        "defense": 20, "mdef": 20, "spd": 20, "luck": 10,
        "accuracy": 90, "evasion": 5, "crit_chance": 10.0, "crit_dmg": 150.0,
    }
    stats_kwargs.update(kwargs)
    return Character(
        user_id=1, name="Test", team=team,
        stats=Stats(**stats_kwargs),
    )


class TestCalculateDamage:
    def test_basic_physical_damage(self):
        attacker = _make_char(atk=50)
        target = _make_char(defense=20)
        effect = SkillEffect(
            effect_type="damage", power=30, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.0,
        )
        result = calculate_damage(attacker, target, effect, seed=42)
        assert result.final_damage > 0
        assert result.raw_damage > 0

    def test_critical_multiplier(self):
        attacker = _make_char(atk=50, crit_dmg=200.0)
        target = _make_char(defense=0)
        effect = SkillEffect(
            effect_type="damage", power=50, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.0,
        )
        normal = calculate_damage(attacker, target, effect, is_critical=False, seed=42)
        crit = calculate_damage(attacker, target, effect, is_critical=True, seed=42)
        assert crit.final_damage > normal.final_damage
        assert crit.is_critical is True

    def test_elemental_resistance_reduces_damage(self):
        attacker = _make_char(matk=50)
        target_no_res = _make_char(fire_res=0.0, mdef=0)
        target_res = _make_char(fire_res=50.0, mdef=0)
        effect = SkillEffect(
            effect_type="damage", power=50, element=Element.FIRE,
            scaling_stat="matk", scaling_ratio=1.0,
        )
        dmg_no_res = calculate_damage(attacker, target_no_res, effect, seed=42)
        dmg_res = calculate_damage(attacker, target_res, effect, seed=42)
        assert dmg_res.final_damage < dmg_no_res.final_damage

    def test_defense_mitigation(self):
        attacker = _make_char(atk=50)
        target_low_def = _make_char(defense=10)
        target_high_def = _make_char(defense=100)
        effect = SkillEffect(
            effect_type="damage", power=50, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.0,
        )
        dmg_low = calculate_damage(attacker, target_low_def, effect, seed=42)
        dmg_high = calculate_damage(attacker, target_high_def, effect, seed=42)
        assert dmg_high.final_damage < dmg_low.final_damage

    def test_shield_absorption(self):
        attacker = _make_char(atk=50)
        target = _make_char(defense=0)
        target.statuses.append(StatusEffect(
            name="Tarcza", status_type=StatusType.SHIELD,
            duration=3, shield_amount=1000.0,
        ))
        effect = SkillEffect(
            effect_type="damage", power=50, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.0,
        )
        result = calculate_damage(attacker, target, effect, seed=42)
        assert result.shield_absorbed > 0
        assert result.final_damage == 0  # all absorbed

    def test_minimum_damage_is_1(self):
        attacker = _make_char(atk=1)
        target = _make_char(defense=999)
        effect = SkillEffect(
            effect_type="damage", power=1, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=0.1,
        )
        result = calculate_damage(attacker, target, effect, seed=42)
        assert result.raw_damage >= 1

    def test_combo_bonus(self):
        attacker = _make_char(atk=50)
        target = _make_char(defense=0)
        effect = SkillEffect(
            effect_type="damage", power=50, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.0,
        )
        normal = calculate_damage(attacker, target, effect, combo_bonus=0.0, seed=42)
        combo = calculate_damage(attacker, target, effect, combo_bonus=0.5, seed=42)
        assert combo.final_damage > normal.final_damage

    def test_lifesteal_calculation(self):
        attacker = _make_char(atk=50)
        attacker.statuses.append(StatusEffect(
            name="Lifesteal", status_type=StatusType.LIFESTEAL,
            duration=3, power=20.0,
        ))
        target = _make_char(defense=0)
        effect = SkillEffect(
            effect_type="damage", power=50, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.0,
        )
        result = calculate_damage(attacker, target, effect, seed=42)
        assert result.lifesteal_heal > 0

    def test_reflect_calculation(self):
        attacker = _make_char(atk=50)
        target = _make_char(defense=0)
        target.statuses.append(StatusEffect(
            name="Reflect", status_type=StatusType.REFLECT,
            duration=3, power=20.0,
        ))
        effect = SkillEffect(
            effect_type="damage", power=50, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.0,
        )
        result = calculate_damage(attacker, target, effect, seed=42)
        assert result.reflected_damage > 0


class TestApplyDamage:
    def test_reduces_hp(self):
        char = _make_char(hp=100, max_hp=100)
        killed = apply_damage(char, 30)
        assert char.stats.hp == 70
        assert killed is False

    def test_kills_at_zero(self):
        char = _make_char(hp=50, max_hp=100)
        killed = apply_damage(char, 50)
        assert char.stats.hp == 0
        assert char.is_alive is False
        assert killed is True

    def test_overkill(self):
        char = _make_char(hp=10, max_hp=100)
        killed = apply_damage(char, 100)
        assert char.stats.hp == 0
        assert killed is True

    def test_wakes_from_sleep(self):
        char = _make_char(hp=100)
        char.statuses.append(StatusEffect(
            name="Sen", status_type=StatusType.SLEEP, duration=2,
        ))
        apply_damage(char, 10)
        assert not char.has_status(StatusType.SLEEP)


class TestHealing:
    def test_basic_heal(self):
        healer = _make_char(matk=50)
        target = _make_char(hp=50, max_hp=500)
        effect = SkillEffect(
            effect_type="heal", power=30,
            scaling_stat="matk", scaling_ratio=1.0,
        )
        amount = calculate_healing(healer, target, effect, seed=42)
        assert amount > 0

    def test_apply_healing_caps_at_max(self):
        char = _make_char(hp=490, max_hp=500)
        actual = apply_healing(char, 100)
        assert char.stats.hp == 500
        assert actual == 10

    def test_apply_healing_full_hp(self):
        char = _make_char(hp=500, max_hp=500)
        actual = apply_healing(char, 50)
        assert actual == 0
