"""
combat.py — Main combat orchestrator.

Ties together all engine modules to run a full Team-vs-Team battle.
Produces a BattleResult with phases for animated display.
"""

from __future__ import annotations

import copy
import random
import time
from typing import Any, Optional

from pvp2 import balance, rng
from pvp2.combos import (
    check_element_combo,
    process_chain_counter,
    process_kill_chain,
    reset_turn_counters,
    update_threat,
)
from pvp2.damage import (
    DamageResult,
    apply_damage,
    apply_healing,
    calculate_damage,
    calculate_healing,
)
from pvp2.effects import (
    apply_status,
    cleanse_debuffs,
    tick_statuses,
)
from pvp2.events import EventBus
from pvp2.models import (
    BattlePhase,
    BattleResult,
    Character,
    Element,
    EventType,
    ResourceType,
    Skill,
    SkillEffect,
    Stats,
    StatusType,
    TargetType,
)
from pvp2.passives import register_all_passives
from pvp2.resources import (
    gain_rage_on_damage_taken,
    gain_rage_on_hit,
    gain_ultimate_charge,
    regen_resources_on_turn,
    spend_resource,
    spend_ultimate,
)
from pvp2.targeting import select_target
from pvp2.timeline import (
    advance_timeline,
    get_next_actor,
    grant_extra_turn,
    initialize_timeline,
    normalize_timeline,
)


class CombatEngine:
    """
    Main combat engine. Runs a full automated battle.

    Usage:
        engine = CombatEngine(team1, team2)
        result = await engine.run()
    """

    def __init__(
        self,
        team1: list[Character],
        team2: list[Character],
        seed: Optional[int] = None,
    ) -> None:
        self.team1 = team1
        self.team2 = team2
        self.all_characters = team1 + team2
        self.event_bus = EventBus()
        self.phases: list[BattlePhase] = []
        self.turn_number = 0
        self.total_damage = 0
        self.damage_tracker: dict[int, int] = {}  # user_id -> total damage dealt
        self.seed = seed
        self._rng = random.Random(seed) if seed else random.Random()

    async def run(self) -> BattleResult:
        """Run the full battle and return the result."""
        start_time = time.time()

        # Register passives
        for char in self.all_characters:
            register_all_passives(self.event_bus, char)

        # Initialize timeline
        initialize_timeline(self.all_characters)

        # Main battle loop
        while self.turn_number < balance.MAX_TURNS:
            # Check win condition
            team1_alive = [c for c in self.team1 if c.is_alive]
            team2_alive = [c for c in self.team2 if c.is_alive]

            if not team1_alive:
                return self._build_result(1, time.time() - start_time)
            if not team2_alive:
                return self._build_result(0, time.time() - start_time)

            # Get next actor
            actor = get_next_actor(self.all_characters)
            if not actor:
                break

            self.turn_number += 1
            reset_turn_counters(actor)

            # Turn start events
            await self.event_bus.emit(EventType.ON_TURN_START, actor=actor)

            # Resource regen
            regen_resources_on_turn(actor)

            # Tick statuses (DOT, HOT, duration)
            status_events = tick_statuses(actor)
            if status_events:
                self._record_status_tick_phase(actor, status_events)

            # Check if actor died from DOT
            if not actor.is_alive:
                continue

            # Check if actor can act (stun, freeze, etc.)
            if not actor.can_act():
                self._record_skip_phase(actor)
                advance_timeline(actor, balance.BASE_ACTION_COST)
                continue

            # Select and execute skill
            await self._execute_turn(actor)

            # Turn end events
            await self.event_bus.emit(EventType.ON_TURN_END, actor=actor)

            # Normalize timeline periodically
            if self.turn_number % 10 == 0:
                normalize_timeline(self.all_characters)

        # Timeout — team with more total HP wins
        return self._build_timeout_result(time.time() - start_time)

    async def _execute_turn(self, actor: Character) -> None:
        """Execute a single turn for an actor."""
        enemies = self._get_enemies(actor)
        allies = self._get_allies(actor)

        # Select best skill
        skill = self._select_skill(actor, enemies, allies)
        if not skill:
            # Basic attack fallback
            skill = self._basic_attack(actor)

        # Check resource cost
        if not spend_resource(actor, skill.resource_type, skill.resource_cost):
            skill = self._basic_attack(actor)

        # Check ultimate cost
        if skill.is_ultimate and skill.ultimate_charge_gain == 0:
            if not spend_ultimate(actor):
                skill = self._basic_attack(actor)

        # Set cooldown
        if skill.cooldown > 0:
            actor.cooldowns[skill.skill_id] = skill.cooldown

        # Select targets
        targets = select_target(
            actor, enemies, allies, skill.target_type,
            strategy="lowest_hp",
        )

        if not targets:
            advance_timeline(actor, skill.action_cost)
            return

        # Execute each effect
        phase = BattlePhase(
            turn_number=self.turn_number,
            actor_name=actor.name,
            actor_emoji=skill.emoji,
            action_name=skill.name,
        )

        for effect in skill.effects:
            effect_targets = self._resolve_effect_targets(
                actor, enemies, allies, effect, targets,
            )

            for target in effect_targets:
                await self._apply_effect(actor, target, effect, skill, phase)

        # Ultimate charge gain
        if not skill.is_ultimate:
            gain_ultimate_charge(actor, skill.ultimate_charge_gain)

        # Record HP bars
        phase.hp_bars = self._get_hp_bars()
        phase.target_names = [t.name for t in targets]
        self.phases.append(phase)

        # Advance timeline
        advance_timeline(actor, skill.action_cost)

        # Kill chain check
        if actor.kills_this_turn > 0:
            grant_extra_turn(actor, balance.CHAIN_KILL_EXTRA_TURN_COST)
            phase.extra_text += "\n⚡ **Zabójstwo!** Dodatkowa tura!"

        # Decrement cooldowns
        for sid in list(actor.cooldowns):
            actor.cooldowns[sid] -= 1
            if actor.cooldowns[sid] <= 0:
                del actor.cooldowns[sid]

    async def _apply_effect(
        self,
        actor: Character,
        target: Character,
        effect: SkillEffect,
        skill: Skill,
        phase: BattlePhase,
    ) -> None:
        """Apply a single skill effect to a target."""

        if effect.effect_type == "damage":
            await self._apply_damage_effect(actor, target, effect, skill, phase)

        elif effect.effect_type == "heal":
            await self._apply_heal_effect(actor, target, effect, phase)

        elif effect.effect_type == "apply_status":
            if effect.status_to_apply:
                success = apply_status(
                    target, effect.status_to_apply,
                    attacker_luck=actor.stats.luck,
                    target_luck=target.stats.luck,
                )
                if success:
                    emoji = effect.status_to_apply.emoji
                    phase.statuses_applied.append(
                        f"{emoji} **{target.name}** — {effect.status_to_apply.name}"
                    )
                    await self.event_bus.emit(
                        EventType.ON_APPLY_STATUS,
                        target=target, attacker=actor,
                        status=effect.status_to_apply,
                    )

        elif effect.effect_type == "shield":
            if effect.status_to_apply:
                apply_status(target, effect.status_to_apply)
                phase.statuses_applied.append(
                    f"🛡️ **{target.name}** — {effect.status_to_apply.name} "
                    f"({int(effect.status_to_apply.shield_amount)} HP)"
                )

        elif effect.effect_type == "remove_status":
            removed = cleanse_debuffs(target, count=3)
            for r in removed:
                phase.statuses_removed.append(
                    f"{r.emoji} **{target.name}** — {r.name} usunięty"
                )
                await self.event_bus.emit(
                    EventType.ON_REMOVE_STATUS,
                    target=target, status=r,
                )

    async def _apply_damage_effect(
        self,
        actor: Character,
        target: Character,
        effect: SkillEffect,
        skill: Skill,
        phase: BattlePhase,
    ) -> None:
        """Apply a damage effect."""
        # Before attack event
        event_result = await self.event_bus.emit(
            EventType.BEFORE_ATTACK,
            attacker=actor, target=target, skill=skill,
        )

        # Hit check
        if not rng.hit_check(
            actor.get_effective_stat("accuracy"),
            actor.stats.luck,
            target.get_effective_stat("evasion"),
            target.stats.luck,
        ):
            phase.is_dodge = True
            await self.event_bus.emit(EventType.ON_DODGE, dodger=target, attacker=actor)
            return

        # Crit check
        is_crit = rng.crit_check(
            actor.get_effective_stat("crit_chance"),
            actor.stats.luck,
            balance.MAX_CRIT_CHANCE,
        )

        # Chain counter bonus
        chain_bonus = process_chain_counter(actor, is_crit)

        # Element combo check
        combo_result = check_element_combo(effect.element, actor.combo_element)
        combo_bonus = combo_result.bonus_damage if combo_result.triggered else 0.0
        actor.combo_element = effect.element

        # Execute bonus (target < 30% HP for execute skill)
        execute_bonus = 0.0
        if skill.skill_id == "execute":
            if target.stats.hp / target.stats.max_hp < 0.3:
                execute_bonus = 0.5

        # Event-based damage bonus
        event_bonus = event_result.get("damage_bonus", 0.0)

        total_combo = chain_bonus + combo_bonus + execute_bonus + event_bonus

        # Calculate damage
        dmg_result = calculate_damage(
            actor, target, effect,
            is_critical=is_crit,
            combo_bonus=total_combo,
        )

        # Apply damage
        killed = apply_damage(target, dmg_result.final_damage)

        # Track damage
        self.total_damage += dmg_result.final_damage
        self.damage_tracker[actor.user_id] = (
            self.damage_tracker.get(actor.user_id, 0) + dmg_result.final_damage
        )

        # Record in phase
        phase.damage_dealt[target.name] = (
            phase.damage_dealt.get(target.name, 0) + dmg_result.final_damage
        )
        phase.is_critical = phase.is_critical or is_crit

        if is_crit:
            await self.event_bus.emit(EventType.ON_CRIT, attacker=actor, target=target, damage=dmg_result.final_damage)

        # Combo phase info
        if combo_result.triggered:
            phase.is_combo = True
            phase.extra_text += f"\n{combo_result.combo_emoji} **{combo_result.combo_name}!** {combo_result.description}"

        # Shield absorption info
        if dmg_result.shield_absorbed > 0:
            phase.extra_text += f"\n🛡️ Tarcza absorbuje **{dmg_result.shield_absorbed}** obrażeń"

        # Lifesteal
        if dmg_result.lifesteal_heal > 0:
            actual_heal = apply_healing(actor, dmg_result.lifesteal_heal)
            if actual_heal > 0:
                phase.healing_done[actor.name] = (
                    phase.healing_done.get(actor.name, 0) + actual_heal
                )

        # Reflect
        if dmg_result.reflected_damage > 0:
            reflect_killed = apply_damage(actor, dmg_result.reflected_damage)
            phase.extra_text += f"\n🪞 Odbicie: **{actor.name}** otrzymuje **{dmg_result.reflected_damage}** obrażeń"
            if reflect_killed:
                phase.kills.append(actor.name)
                await self.event_bus.emit(
                    EventType.ON_DEATH, target=actor, killer=target,
                )

        # Rage gains
        gain_rage_on_hit(actor, dmg_result.final_damage)
        gain_rage_on_damage_taken(target, dmg_result.final_damage)

        # Ultimate charge
        gain_ultimate_charge(actor, max(5, dmg_result.final_damage // 10))
        gain_ultimate_charge(target, max(3, dmg_result.final_damage // 15))

        # On damage event
        await self.event_bus.emit(
            EventType.ON_DAMAGE,
            target=target, attacker=actor, damage=dmg_result.final_damage,
        )

        # Kill handling
        if killed:
            phase.kills.append(target.name)
            actor.kills_this_turn += 1
            update_threat(actor, dmg_result.final_damage, 0)
            await self.event_bus.emit(
                EventType.ON_KILL, killer=actor, victim=target,
            )
            await self.event_bus.emit(
                EventType.ON_DEATH, target=target, killer=actor,
            )

    async def _apply_heal_effect(
        self,
        actor: Character,
        target: Character,
        effect: SkillEffect,
        phase: BattlePhase,
    ) -> None:
        """Apply a healing effect."""
        heal_amount = calculate_healing(actor, target, effect)
        actual = apply_healing(target, heal_amount)
        if actual > 0:
            phase.healing_done[target.name] = (
                phase.healing_done.get(target.name, 0) + actual
            )
            update_threat(actor, 0, actual)
            await self.event_bus.emit(
                EventType.ON_HEAL, healer=actor, target=target, amount=actual,
            )

    def _select_skill(
        self,
        actor: Character,
        enemies: list[Character],
        allies: list[Character],
    ) -> Optional[Skill]:
        """
        AI skill selection. Picks the best available skill.
        Priority: ultimate > heal if ally low > AoE if multiple enemies > single target
        """
        available: list[Skill] = []
        for skill in actor.skills:
            # Check cooldown
            if skill.skill_id in actor.cooldowns:
                continue
            # Check silence (can't cast spells)
            if not actor.can_cast() and skill.resource_type == ResourceType.MANA:
                continue
            # Check resource
            from pvp2.resources import get_resource
            if get_resource(actor, skill.resource_type) < skill.resource_cost:
                continue
            # Check ultimate charge
            if skill.is_ultimate and skill.ultimate_charge_gain == 0:
                from pvp2.resources import can_use_ultimate
                if not can_use_ultimate(actor):
                    continue
            available.append(skill)

        if not available:
            return None

        # Priority scoring
        def skill_score(s: Skill) -> float:
            score = 0.0
            # Ultimate bonus
            if s.is_ultimate:
                score += 100

            # Heal priority when ally is low
            has_heal = any(e.effect_type == "heal" for e in s.effects)
            if has_heal:
                ally_low = any(
                    a.is_alive and a.stats.hp < a.stats.max_hp * 0.4
                    for a in allies
                )
                if ally_low:
                    score += 80

            # AoE bonus when multiple enemies
            alive_enemies = sum(1 for e in enemies if e.is_alive)
            if s.target_type in (TargetType.ALL_ENEMIES, TargetType.ALL_ALLIES):
                score += alive_enemies * 10

            # Damage score
            for eff in s.effects:
                if eff.effect_type == "damage":
                    score += eff.power * eff.scaling_ratio * 0.5
                elif eff.effect_type == "apply_status":
                    score += 15

            # Add some randomness
            score += self._rng.uniform(-5, 5)
            return score

        available.sort(key=skill_score, reverse=True)
        return available[0]

    def _basic_attack(self, actor: Character) -> Skill:
        """Create a basic attack skill for fallback."""
        return Skill(
            skill_id="basic_attack",
            name="Atak Podstawowy",
            description="Zwykły atak.",
            emoji="⚔️",
            element=Element.PHYSICAL,
            target_type=TargetType.SINGLE_ENEMY,
            effects=[
                SkillEffect(
                    effect_type="damage", power=10,
                    element=Element.PHYSICAL,
                    scaling_stat="atk", scaling_ratio=1.0,
                ),
            ],
            action_cost=100,
        )

    def _resolve_effect_targets(
        self,
        actor: Character,
        enemies: list[Character],
        allies: list[Character],
        effect: SkillEffect,
        default_targets: list[Character],
    ) -> list[Character]:
        """Resolve targets for a specific effect within a skill."""
        if effect.target == TargetType.SELF:
            return [actor]
        if effect.target == TargetType.ALL_ENEMIES:
            return [e for e in enemies if e.is_alive]
        if effect.target == TargetType.ALL_ALLIES:
            return [a for a in allies if a.is_alive]
        if effect.target == TargetType.SINGLE_ALLY:
            # Find lowest HP ally for heals
            alive_allies = [a for a in allies if a.is_alive]
            if alive_allies:
                return [min(alive_allies, key=lambda a: a.stats.hp)]
            return []
        return default_targets

    def _get_enemies(self, actor: Character) -> list[Character]:
        """Get enemies of an actor."""
        if actor.team == 0:
            return self.team2
        return self.team1

    def _get_allies(self, actor: Character) -> list[Character]:
        """Get allies of an actor (including self)."""
        if actor.team == 0:
            return self.team1
        return self.team2

    def _get_hp_bars(self) -> dict[str, tuple[int, int]]:
        """Get current HP bars for all characters."""
        return {
            c.name: (c.stats.hp, c.stats.max_hp)
            for c in self.all_characters
        }

    def _record_status_tick_phase(self, actor: Character, events: list[dict]) -> None:
        """Record a phase for status ticks."""
        phase = BattlePhase(
            turn_number=self.turn_number,
            actor_name=actor.name,
            actor_emoji="🔄",
            action_name="Efekty statusów",
        )

        for event in events:
            if event["type"] == "dot_tick":
                phase.damage_dealt[event["target"]] = (
                    phase.damage_dealt.get(event["target"], 0) + event["damage"]
                )
                phase.description += (
                    f"{event['emoji']} **{event['name']}** zadaje "
                    f"**{event['damage']}** obrażeń {event['target']}\n"
                )
            elif event["type"] in ("hot_tick", "freeze_tick"):
                if "heal" in event:
                    phase.healing_done[event["target"]] = (
                        phase.healing_done.get(event["target"], 0) + event["heal"]
                    )
                if "damage" in event:
                    phase.damage_dealt[event["target"]] = (
                        phase.damage_dealt.get(event["target"], 0) + event["damage"]
                    )
            elif event["type"] == "status_expired":
                phase.statuses_removed.append(
                    f"{event['emoji']} **{event['target']}** — {event['name']} wygasł"
                )

        if not actor.is_alive:
            phase.kills.append(actor.name)

        phase.hp_bars = self._get_hp_bars()
        self.phases.append(phase)

    def _record_skip_phase(self, actor: Character) -> None:
        """Record a phase when actor's turn is skipped."""
        cc_names = [s.name for s in actor.statuses if s.prevents_action]
        reason = ", ".join(cc_names) if cc_names else "efekt statusu"
        phase = BattlePhase(
            turn_number=self.turn_number,
            actor_name=actor.name,
            actor_emoji="⏭️",
            action_name="Pominięty",
            description=f"**{actor.name}** nie może działać — {reason}!",
            hp_bars=self._get_hp_bars(),
        )
        self.phases.append(phase)

    def _build_result(self, winning_team: int, duration: float) -> BattleResult:
        """Build the final battle result."""
        if winning_team == 0:
            winners = [c for c in self.team1]
            losers = [c for c in self.team2]
        else:
            winners = [c for c in self.team2]
            losers = [c for c in self.team1]

        # MVP = highest damage dealer
        mvp = None
        if self.damage_tracker:
            mvp_id = max(self.damage_tracker, key=self.damage_tracker.get)  # type: ignore
            for c in self.all_characters:
                if c.user_id == mvp_id:
                    mvp = c
                    break

        return BattleResult(
            winning_team=winning_team,
            winners=winners,
            losers=losers,
            phases=self.phases,
            total_turns=self.turn_number,
            total_damage=self.total_damage,
            mvp=mvp,
            duration_seconds=duration,
        )

    def _build_timeout_result(self, duration: float) -> BattleResult:
        """Build result when battle times out."""
        team1_hp = sum(c.stats.hp for c in self.team1 if c.is_alive)
        team2_hp = sum(c.stats.hp for c in self.team2 if c.is_alive)
        winning_team = 0 if team1_hp >= team2_hp else 1
        return self._build_result(winning_team, duration)


# ──────────────────── Helper: Build Character from DB ────────────────────


def build_character_from_db(
    player_data: dict[str, Any],
    deck_skills: list[Skill],
    team: int,
) -> Character:
    """Build a Character from database player data and deck skills."""
    from pvp2.balance import get_prestige_tier_data

    prestige = player_data.get("prestige_tier", 0)
    tier_data = get_prestige_tier_data(prestige)

    stats = Stats(
        hp=player_data["max_hp"] + tier_data["flat_hp"],
        max_hp=player_data["max_hp"] + tier_data["flat_hp"],
        atk=player_data["atk"] + tier_data["flat_atk"],
        matk=player_data["matk"] + tier_data["flat_matk"],
        defense=player_data["defense"],
        mdef=player_data["mdef"],
        spd=player_data["spd"],
        luck=player_data["luck"],
        accuracy=player_data["accuracy"],
        evasion=player_data["evasion"],
        crit_chance=player_data["crit_chance"],
        crit_dmg=player_data["crit_dmg"],
        mana=player_data["max_mana"],
        max_mana=player_data["max_mana"],
        rage=0,
        max_rage=player_data["max_rage"],
        energy=player_data["max_energy"],
        max_energy=player_data["max_energy"],
    )

    return Character(
        user_id=player_data["user_id"],
        name=player_data["name"],
        team=team,
        stats=stats,
        level=player_data["level"],
        prestige_tier=prestige,
        skills=deck_skills,
    )
