"""
duel_cog.py — Cog 1: ^duel command with animated combat display.

Usage: ^duel @user1 @user2 ...
Creates teams and runs an automated battle with animated embed updates.
"""

from __future__ import annotations

import asyncio
import copy
from typing import Optional

import discord
from discord.ext import commands

from pvp2.combat import CombatEngine, build_character_from_db
from pvp2.db import get_db
from pvp2.embeds import build_animation_frames, battle_summary_embed
from pvp2.models import Skill
from pvp2.rng import generate_battle_seed
from pvp2.skills import get_skill


class DuelCog(commands.Cog, name="PvP Duel"):
    """Cog obsługujący komendy walki PvP."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._active_duels: set[int] = set()  # channel IDs with active duels

    @commands.command(name="duel")
    async def duel(self, ctx: commands.Context, *mentions: discord.Member) -> None:
        """
        Rozpocznij walkę PvP!

        Użycie: ^duel @gracz1 @gracz2 ...
        - 1 mention = 1v1 (Ty vs gracz)
        - 2+ mentions = Team vs Team (dzieli graczy na dwie drużyny)
        """
        if ctx.channel.id in self._active_duels:
            await ctx.send("⚠️ Na tym kanale trwa już walka! Poczekaj na zakończenie.")
            return

        if not mentions:
            await ctx.send("⚔️ Użycie: `^duel @gracz1 [@gracz2 ...]`")
            return

        # Collect all participants (author + mentions)
        participants = [ctx.author]
        for member in mentions:
            if member.bot:
                await ctx.send("🤖 Nie możesz walczyć z botem!")
                return
            if member.id == ctx.author.id:
                continue
            if member not in participants:
                participants.append(member)

        if len(participants) < 2:
            await ctx.send("⚠️ Potrzebujesz przynajmniej 2 graczy do walki!")
            return

        if len(participants) > 10:
            await ctx.send("⚠️ Maksymalnie 10 graczy w jednej walce!")
            return

        self._active_duels.add(ctx.channel.id)

        try:
            await self._run_duel(ctx, participants)
        finally:
            self._active_duels.discard(ctx.channel.id)

    async def _run_duel(
        self, ctx: commands.Context, participants: list[discord.Member]
    ) -> None:
        """Run the full duel flow."""
        db = await get_db()

        # Ensure all players exist in DB (auto-registration)
        for member in participants:
            await db.get_or_create_player(member.id, name=member.display_name)

        # Split into teams
        mid = len(participants) // 2
        team1_members = participants[:mid] if mid > 0 else [participants[0]]
        team2_members = participants[mid:] if mid > 0 else participants[1:]

        # Handle 1v1 specifically
        if len(participants) == 2:
            team1_members = [participants[0]]
            team2_members = [participants[1]]

        # Build characters from DB data
        team1 = []
        team2 = []

        for member in team1_members:
            char = await self._build_character(db, member, team=0)
            team1.append(char)

        for member in team2_members:
            char = await self._build_character(db, member, team=1)
            team2.append(char)

        # Send initial message
        team1_names = ", ".join(m.display_name for m in team1_members)
        team2_names = ", ".join(m.display_name for m in team2_members)

        embed = discord.Embed(
            title="⚔️ Bitwa się rozpoczyna!",
            description=(
                f"**Drużyna 1:** {team1_names}\n"
                f"**Drużyna 2:** {team2_names}\n\n"
                f"⏳ Przygotowanie..."
            ),
            color=0x546E7A,
        )
        message = await ctx.send(embed=embed)
        await asyncio.sleep(1.5)

        # Run combat
        seed = generate_battle_seed([m.id for m in participants])
        engine = CombatEngine(team1, team2, seed=seed)
        result = await engine.run()

        # Animate phases
        frames = build_animation_frames(result, phases_per_frame=3)

        for i, frame_data in enumerate(frames):
            frame_embed = discord.Embed.from_dict(frame_data)
            try:
                await message.edit(embed=frame_embed)
            except discord.HTTPException:
                pass
            # Delay between frames (faster for middle, slower for start/end)
            if i == 0 or i == len(frames) - 1:
                await asyncio.sleep(2.0)
            else:
                await asyncio.sleep(1.2)

        # Record battle results in DB
        winner_team = result.winning_team
        all_ids = [m.id for m in participants]
        team1_ids = [m.id for m in team1_members]
        team2_ids = [m.id for m in team2_members]
        mvp_id = result.mvp.user_id if result.mvp else 0

        await db.record_battle(
            guild_id=ctx.guild.id if ctx.guild else 0,
            team1_ids=team1_ids,
            team2_ids=team2_ids,
            winner_team=winner_team,
            total_turns=result.total_turns,
            mvp_id=mvp_id,
            log_summary=f"Drużyna {winner_team + 1} wygrywa po {result.total_turns} turach.",
        )

        # Update win/loss stats
        winner_ids = team1_ids if winner_team == 0 else team2_ids
        for pid in all_ids:
            player = await db.get_or_create_player(pid)
            new_battles = player["total_battles"] + 1
            updates = {"total_battles": new_battles}
            if pid in winner_ids:
                updates["total_wins"] = player["total_wins"] + 1
            await db.update_player(pid, **updates)

    async def _build_character(
        self, db, member: discord.Member, team: int
    ):
        """Build a combat Character from DB data."""
        player_data = await db.get_or_create_player(member.id, name=member.display_name)

        # Update name if changed
        if player_data["name"] != member.display_name:
            await db.update_player(member.id, name=member.display_name)
            player_data["name"] = member.display_name

        # Get deck skills
        deck = await db.get_deck(member.id)
        deck_skills: list[Skill] = []
        for skill_id in deck:
            if skill_id:
                skill_obj = get_skill(skill_id)
                if skill_obj:
                    deck_skills.append(copy.deepcopy(skill_obj))

        return build_character_from_db(player_data, deck_skills, team)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DuelCog(bot))
