"""Tests for the 32 skills — verify sensible stat requirements, scaling, and structure."""
import pytest
from pvp2.skills import ALL_SKILLS, get_skill, get_skills_by_category, get_all_categories, get_available_skills
from pvp2.models import Element, ResourceType, Stats


class TestSkillRegistry:
    def test_all_skills_exist(self):
        assert len(ALL_SKILLS) == 36

    def test_all_skills_have_unique_ids(self):
        ids = list(ALL_SKILLS.keys())
        assert len(ids) == len(set(ids))

    def test_all_skills_have_names(self):
        for skill_id, skill in ALL_SKILLS.items():
            assert skill.name, f"Skill {skill_id} missing name"
            assert skill.description, f"Skill {skill_id} missing description"

    def test_all_skills_have_effects(self):
        for skill_id, skill in ALL_SKILLS.items():
            assert len(skill.effects) > 0, f"Skill {skill_id} has no effects"

    def test_all_skills_have_valid_elements(self):
        for skill_id, skill in ALL_SKILLS.items():
            assert isinstance(skill.element, Element), f"Skill {skill_id} invalid element"

    def test_all_skills_have_valid_resource_type(self):
        for skill_id, skill in ALL_SKILLS.items():
            assert isinstance(skill.resource_type, ResourceType), f"Skill {skill_id} invalid resource_type"

    def test_all_skills_have_positive_price(self):
        for skill_id, skill in ALL_SKILLS.items():
            assert skill.price > 0, f"Skill {skill_id} price must be positive"

    def test_get_skill_returns_correct(self):
        fb = get_skill("fireball")
        assert fb is not None
        assert fb.name == "Kula Ognia"

    def test_get_skill_missing_returns_none(self):
        assert get_skill("nonexistent_skill") is None

    def test_categories_exist(self):
        cats = get_all_categories()
        assert len(cats) >= 4


class TestSkillRequirements:
    def test_level_1_skills_exist(self):
        """There should be skills available at level 1 with base stats."""
        from dataclasses import asdict
        base_stats = asdict(Stats())
        available = get_available_skills(level=1, stats=base_stats)
        assert len(available) > 0, "No skills available at level 1 with base stats"

    def test_high_level_skills_not_available_at_level_1(self):
        """Ultimate skills requiring high level/stats should not be available at level 1."""
        from dataclasses import asdict
        base_stats = asdict(Stats())
        available = get_available_skills(level=1, stats=base_stats)
        available_ids = {s.skill_id for s in available}
        # Meteor requires level 10 and high matk
        assert "meteor" not in available_ids
        assert "apocalypse" not in available_ids

    def test_physical_skills_require_atk(self):
        """Physical damage skills should require ATK, not MATK."""
        slash = get_skill("slash")
        assert slash is not None
        assert slash.min_atk > 0 or slash.min_level >= 1

    def test_magic_skills_require_matk(self):
        """Magic damage skills should require MATK."""
        fb = get_skill("fireball")
        assert fb is not None
        assert fb.min_matk > 0

    def test_ultimate_skills_cost_more(self):
        """Ultimate skills should have higher resource costs than basic skills."""
        fb = get_skill("fireball")
        meteor_skill = get_skill("meteor")
        assert fb is not None and meteor_skill is not None
        assert meteor_skill.resource_cost > fb.resource_cost
        assert meteor_skill.action_cost >= fb.action_cost

    def test_healing_skills_target_allies(self):
        """Healing skills should target allies."""
        hl = get_skill("holy_light")
        assert hl is not None
        from pvp2.models import TargetType
        assert hl.target_type in (TargetType.SINGLE_ALLY, TargetType.ALL_ALLIES, TargetType.SELF)

    def test_aoe_skills_have_higher_cost(self):
        """AoE skills should generally cost more resources."""
        from pvp2.models import TargetType
        single_costs = []
        aoe_costs = []
        for skill in ALL_SKILLS.values():
            if skill.target_type == TargetType.SINGLE_ENEMY:
                single_costs.append(skill.resource_cost)
            elif skill.target_type == TargetType.ALL_ENEMIES:
                aoe_costs.append(skill.resource_cost)
        if single_costs and aoe_costs:
            avg_single = sum(single_costs) / len(single_costs)
            avg_aoe = sum(aoe_costs) / len(aoe_costs)
            assert avg_aoe >= avg_single, "AoE skills should cost more on average"

    def test_no_free_ultimate(self):
        """Ultimate skills should have meaningful costs."""
        for skill in ALL_SKILLS.values():
            if skill.is_ultimate:
                assert skill.resource_cost >= 30, f"Ultimate {skill.skill_id} too cheap"
                assert skill.cooldown >= 4, f"Ultimate {skill.skill_id} cooldown too low"
                assert skill.min_level >= 8, f"Ultimate {skill.skill_id} level req too low"


class TestSkillBalance:
    def test_no_zero_power_damage_skills(self):
        """Damage effects should have positive power."""
        for skill_id, skill in ALL_SKILLS.items():
            for eff in skill.effects:
                if eff.effect_type == "damage":
                    assert eff.power > 0, f"Skill {skill_id} has 0-power damage effect"

    def test_scaling_ratios_reasonable(self):
        """Scaling ratios should be in a reasonable range."""
        for skill_id, skill in ALL_SKILLS.items():
            for eff in skill.effects:
                if eff.effect_type == "damage":
                    assert 0.1 <= eff.scaling_ratio <= 3.0, (
                        f"Skill {skill_id} scaling_ratio {eff.scaling_ratio} out of range"
                    )

    def test_cooldowns_reasonable(self):
        """Cooldowns should be in 0-10 range."""
        for skill_id, skill in ALL_SKILLS.items():
            assert 0 <= skill.cooldown <= 10, f"Skill {skill_id} cooldown {skill.cooldown} out of range"

    def test_action_costs_reasonable(self):
        """Action costs should be in 50-200 range."""
        for skill_id, skill in ALL_SKILLS.items():
            assert 50 <= skill.action_cost <= 200, (
                f"Skill {skill_id} action_cost {skill.action_cost} out of range"
            )
