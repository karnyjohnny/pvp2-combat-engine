"""
embeds.py — Combat log & Discord embed generator.

Generates narrative combat logs in Polish, formatted as Discord embeds
with emoji, colors, HP bars, and animation steps (phases).
"""

from __future__ import annotations

from typing import Any

from pvp2.models import BattlePhase, BattleResult, Character


# ──────────────────── Colors ────────────────────

COLOR_ATTACK = 0xE74C3C    # red
COLOR_HEAL = 0x2ECC71      # green
COLOR_BUFF = 0x3498DB      # blue
COLOR_DEBUFF = 0x9B59B6    # purple
COLOR_COMBO = 0xF39C12     # orange
COLOR_KILL = 0x1F1F1F      # dark
COLOR_VICTORY = 0xFFD700   # gold
COLOR_DEFEAT = 0x95A5A6    # gray
COLOR_NEUTRAL = 0x546E7A   # blue-gray

TEAM_COLORS = [0x3498DB, 0xE74C3C]  # blue vs red


# ──────────────────── HP Bar ────────────────────

def hp_bar(current: int, maximum: int, length: int = 10) -> str:
    """Generate a visual HP bar."""
    if maximum <= 0:
        return "░" * length
    ratio = max(0.0, min(1.0, current / maximum))
    filled = int(ratio * length)
    empty = length - filled
    if ratio > 0.5:
        bar = "█" * filled + "░" * empty
    elif ratio > 0.25:
        bar = "▓" * filled + "░" * empty
    else:
        bar = "▒" * filled + "░" * empty
    pct = int(ratio * 100)
    return f"`{bar}` {current}/{maximum} ({pct}%)"


# ──────────────────── Phase to Embed ────────────────────

def phase_to_embed_dict(phase: BattlePhase, turn_total: int) -> dict[str, Any]:
    """
    Convert a BattlePhase to a Discord embed dict payload.

    Returns a dict compatible with discord.Embed.from_dict().
    """
    # Determine color based on phase content
    if phase.kills:
        color = COLOR_KILL
    elif phase.is_combo:
        color = COLOR_COMBO
    elif phase.is_critical:
        color = COLOR_ATTACK
    elif phase.healing_done:
        color = COLOR_HEAL
    elif phase.statuses_applied:
        color = COLOR_DEBUFF
    else:
        color = COLOR_NEUTRAL

    # Build description
    lines: list[str] = []

    if phase.description:
        lines.append(phase.description)

    # Damage
    for name, dmg in phase.damage_dealt.items():
        crit_text = " **KRYTYK!**" if phase.is_critical else ""
        lines.append(f"💥 **{name}** otrzymuje **{dmg}** obrażeń{crit_text}")

    # Dodge
    if phase.is_dodge:
        target_names = ", ".join(phase.target_names) if phase.target_names else "cel"
        lines.append(f"💨 **{target_names}** unika ataku!")

    # Healing
    for name, heal in phase.healing_done.items():
        lines.append(f"💚 **{name}** odzyskuje **{heal}** HP")

    # Statuses applied
    for status_text in phase.statuses_applied:
        lines.append(f"🔄 {status_text}")

    # Statuses removed
    for status_text in phase.statuses_removed:
        lines.append(f"❌ {status_text}")

    # Kills
    for kill_name in phase.kills:
        lines.append(f"☠️ **{kill_name}** poległ!")

    # Combo
    if phase.is_combo:
        lines.append(f"🔗 **COMBO!** Żywiołowa reakcja łańcuchowa!")

    # Extra text
    if phase.extra_text:
        lines.append(phase.extra_text)

    description = "\n".join(lines) if lines else "..."

    # HP bars for all characters
    hp_fields: list[dict[str, Any]] = []
    for name, (cur_hp, max_hp) in phase.hp_bars.items():
        hp_fields.append({
            "name": name,
            "value": hp_bar(cur_hp, max_hp),
            "inline": True,
        })

    embed: dict[str, Any] = {
        "title": f"⚔️ Tura {phase.turn_number}/{turn_total}",
        "description": description,
        "color": color,
        "fields": hp_fields,
        "footer": {
            "text": f"{phase.actor_emoji} {phase.actor_name} → {phase.action_name}",
        },
    }

    return embed


# ──────────────────── Battle Summary Embed ────────────────────

def battle_summary_embed(result: BattleResult) -> dict[str, Any]:
    """Generate final battle summary embed."""
    winner_names = ", ".join(c.name for c in result.winners)
    loser_names = ", ".join(c.name for c in result.losers)
    mvp_text = f"🏆 MVP: **{result.mvp.name}**" if result.mvp else ""

    fields: list[dict[str, Any]] = [
        {
            "name": "🏅 Zwycięzcy",
            "value": winner_names or "Brak",
            "inline": True,
        },
        {
            "name": "💀 Pokonani",
            "value": loser_names or "Brak",
            "inline": True,
        },
        {
            "name": "📊 Statystyki",
            "value": (
                f"⚔️ Tur: **{result.total_turns}**\n"
                f"💥 Łączne obrażenia: **{result.total_damage}**\n"
                f"⏱️ Czas: **{result.duration_seconds:.1f}s**"
            ),
            "inline": False,
        },
    ]

    if mvp_text:
        fields.append({
            "name": "🌟 Wyróżnienie",
            "value": mvp_text,
            "inline": False,
        })

    # Survivor HP bars
    survivor_lines = []
    for c in result.winners:
        survivor_lines.append(f"{c.name}: {hp_bar(c.stats.hp, c.stats.max_hp, 8)}")

    if survivor_lines:
        fields.append({
            "name": "❤️ HP Zwycięzców",
            "value": "\n".join(survivor_lines),
            "inline": False,
        })

    return {
        "title": f"🏆 Zwycięstwo — Drużyna {result.winning_team + 1}!",
        "description": f"Bitwa zakończona po **{result.total_turns}** turach.",
        "color": COLOR_VICTORY,
        "fields": fields,
    }


# ──────────────────── Animation Frame Builder ────────────────────

def build_animation_frames(
    result: BattleResult,
    phases_per_frame: int = 3,
) -> list[dict[str, Any]]:
    """
    Build a sequence of embed dicts for animated display.
    Groups phases into frames for message editing animation.

    Returns list of embed dicts to be shown one by one.
    """
    frames: list[dict[str, Any]] = []

    # Opening frame
    team1_names = [c.name for c in result.winners + result.losers if c.team == 0]
    team2_names = [c.name for c in result.winners + result.losers if c.team == 1]

    frames.append({
        "title": "⚔️ Bitwa się rozpoczyna!",
        "description": (
            f"**Drużyna 1:** {', '.join(team1_names)}\n"
            f"**Drużyna 2:** {', '.join(team2_names)}\n\n"
            f"Przygotujcie się..."
        ),
        "color": COLOR_NEUTRAL,
        "fields": [],
    })

    # Phase frames
    for i in range(0, len(result.phases), phases_per_frame):
        chunk = result.phases[i:i + phases_per_frame]
        combined_desc_lines: list[str] = []
        combined_fields: list[dict[str, Any]] = []
        last_phase = chunk[-1]

        for phase in chunk:
            phase_embed = phase_to_embed_dict(phase, result.total_turns)
            header = f"**{phase.actor_emoji} {phase.actor_name}** → _{phase.action_name}_"
            combined_desc_lines.append(header)
            combined_desc_lines.append(phase_embed["description"])
            combined_desc_lines.append("")

        # HP bars from the last phase
        for name, (cur_hp, max_hp) in last_phase.hp_bars.items():
            combined_fields.append({
                "name": name,
                "value": hp_bar(cur_hp, max_hp),
                "inline": True,
            })

        color = COLOR_ATTACK
        if any(p.kills for p in chunk):
            color = COLOR_KILL
        elif any(p.is_combo for p in chunk):
            color = COLOR_COMBO
        elif any(p.is_critical for p in chunk):
            color = COLOR_ATTACK

        frames.append({
            "title": f"⚔️ Tura {chunk[0].turn_number}–{last_phase.turn_number}",
            "description": "\n".join(combined_desc_lines),
            "color": color,
            "fields": combined_fields,
        })

    # Summary frame
    frames.append(battle_summary_embed(result))

    return frames


# ──────────────────── Turn Order Preview ────────────────────

def turn_order_embed(characters: list[Character]) -> dict[str, Any]:
    """Generate a turn order preview embed."""
    lines = []
    for i, char in enumerate(characters[:8], 1):
        status_icons = " ".join(s.emoji for s in char.statuses if s.emoji)
        hp_text = hp_bar(char.stats.hp, char.stats.max_hp, 6)
        lines.append(
            f"**{i}.** {char.name} {status_icons}\n"
            f"   {hp_text}"
        )

    return {
        "title": "📋 Kolejka Inicjatywy",
        "description": "\n".join(lines),
        "color": COLOR_NEUTRAL,
        "fields": [],
    }


# ──────────────────── Status List Embed ────────────────────

def status_list_embed(character: Character) -> dict[str, Any]:
    """Generate embed showing all active statuses on a character."""
    if not character.statuses:
        desc = "_Brak aktywnych efektów._"
    else:
        lines = []
        for s in character.statuses:
            lines.append(f"{s.emoji} **{s.name}** — {s.description} (📍 {s.duration} tur)")
        desc = "\n".join(lines)

    return {
        "title": f"📜 Statusy — {character.name}",
        "description": desc,
        "color": COLOR_BUFF,
        "fields": [],
    }
