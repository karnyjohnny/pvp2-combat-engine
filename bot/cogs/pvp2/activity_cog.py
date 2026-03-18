"""
activity_cog.py — Cog 2: Activity rewards, deck management, shop.

Features:
- XP/gold for messages (anti-spam, engagement scoring)
- XP/gold for voice channel activity
- ^deck — view/edit skill deck (5 slots, interactive UI)
- ^sklep — paginated shop with buy buttons
- ^kup <id> — buy a skill
- ^sprzedaj <id> — sell a skill
"""

from __future__ import annotations

import asyncio
import math
import re
import time
from typing import Optional

import discord
from discord.ext import commands, tasks

from pvp2.balance import (
    MESSAGE_COOLDOWN_SECONDS,
    MIN_MESSAGE_LENGTH,
    VOICE_GOLD_PER_MINUTE,
    VOICE_REWARD_INTERVAL,
    VOICE_XP_PER_MINUTE,
    calculate_message_rewards,
    get_prestige_tier_data,
    xp_for_level,
)
from pvp2.db import get_db
from pvp2.skills import ALL_SKILLS, get_shop_page, get_skill


# ──────────────────── Deck View ────────────────────


class DeckEditSelect(discord.ui.Select):
    """Dropdown to select skills for deck."""

    def __init__(self, owned_skills: list[str], current_deck: list[Optional[str]]) -> None:
        options = []
        for sid in owned_skills:
            skill = get_skill(sid)
            if skill:
                is_in_deck = sid in current_deck
                options.append(discord.SelectOption(
                    label=skill.name,
                    value=skill.skill_id,
                    description=skill.description[:50],
                    emoji=skill.emoji,
                    default=is_in_deck,
                ))

        # Limit to 25 options (Discord max)
        options = options[:25]

        super().__init__(
            placeholder="Wybierz 1–5 skilli do decku...",
            min_values=0,
            max_values=min(5, len(options)),
            options=options if options else [discord.SelectOption(label="Brak skilli", value="none")],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values
        if "none" in selected:
            selected = []
        # Store selection for the save button
        self.view.selected_skills = selected  # type: ignore
        await interaction.response.defer()


class DeckEditView(discord.ui.View):
    """View for editing deck with dropdown + save/cancel buttons."""

    def __init__(self, user_id: int, owned_skills: list[str], current_deck: list[Optional[str]]) -> None:
        super().__init__(timeout=120)
        self.user_id = user_id
        self.selected_skills: list[str] = [s for s in current_deck if s]
        self.saved = False

        if owned_skills:
            self.add_item(DeckEditSelect(owned_skills, current_deck))

    @discord.ui.button(label="💾 Zapisz deck", style=discord.ButtonStyle.success)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("To nie twój deck!", ephemeral=True)
            return

        db = await get_db()
        await db.set_deck(self.user_id, self.selected_skills[:5])
        self.saved = True

        # Build updated deck embed
        embed = await _build_deck_embed(self.user_id, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="✖ Anuluj", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("To nie twój deck!", ephemeral=True)
            return
        await interaction.response.edit_message(view=None)
        self.stop()


class DeckView(discord.ui.View):
    """View for displaying deck with edit button."""

    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="✏️ Edytuj deck", style=discord.ButtonStyle.primary)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("To nie twój deck!", ephemeral=True)
            return

        db = await get_db()
        owned = await db.get_player_skills(self.user_id)
        deck = await db.get_deck(self.user_id)

        if not owned:
            await interaction.response.send_message(
                "🎴 Nie posiadasz żadnych skilli! Kup je w `^sklep`.",
                ephemeral=True,
            )
            return

        edit_view = DeckEditView(self.user_id, owned, deck)
        embed = discord.Embed(
            title="🎴 Wybierz skille do decku",
            description="Wybierz 1–5 skilli z listy poniżej.",
            color=0x3498DB,
        )
        await interaction.response.send_message(embed=embed, view=edit_view, ephemeral=True)


# ──────────────────── Shop View ────────────────────


class ShopView(discord.ui.View):
    """Paginated shop view."""

    def __init__(self, user_id: int, page: int = 1) -> None:
        super().__init__(timeout=300)
        self.user_id = user_id
        self.page = page

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("To nie twój sklep!", ephemeral=True)
            return
        self.page = max(1, self.page - 1)
        embed = await _build_shop_embed(self.user_id, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="1 / 1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("To nie twój sklep!", ephemeral=True)
            return
        _, total = get_shop_page(self.page)
        self.page = min(total, self.page + 1)
        embed = await _build_shop_embed(self.user_id, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    async def update_page_indicator(self) -> None:
        _, total = get_shop_page(self.page)
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.disabled:
                child.label = f"{self.page} / {total}"
                break


# ──────────────────── Helper Functions ────────────────────


async def _build_deck_embed(user_id: int, display_name: str) -> discord.Embed:
    """Build deck display embed."""
    db = await get_db()
    deck = await db.get_deck(user_id)
    owned = await db.get_player_skills(user_id)

    used_count = sum(1 for s in deck if s)

    embed = discord.Embed(
        title=f"⚔️ Aktywny deck — {display_name}",
        description=f"Używane w walce: **{used_count}/5** skilli\nKolekcja: **{len(owned)}** skilli",
        color=0x3498DB,
    )

    for i in range(5):
        skill_id = deck[i] if i < len(deck) else None
        if skill_id:
            skill = get_skill(skill_id)
            if skill:
                slot_text = f"{skill.emoji} {skill.name}"
            else:
                slot_text = "❓ Nieznany skill"
        else:
            slot_text = "░░░ pusty slot"

        slot_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        embed.add_field(
            name=f"{slot_emojis[i]} Slot {i + 1}",
            value=slot_text,
            inline=False,
        )

    return embed


async def _build_shop_embed(user_id: int, page: int = 1) -> discord.Embed:
    """Build shop page embed."""
    db = await get_db()
    player = await db.get_or_create_player(user_id)
    owned = await db.get_player_skills(user_id)
    skills, total_pages = get_shop_page(page, per_page=5)

    embed = discord.Embed(
        title=f"🏪 Sklep Umiejętności   •   strona {page}/{total_pages}",
        description=f"💰 **{player['gold']}** 🪙  •  poziom **{player['level']}**\n{'─' * 40}",
        color=0xF39C12,
    )

    for skill in skills:
        # Status indicator
        if skill.skill_id in owned:
            status = "✅  Posiadasz"
        elif player["level"] < skill.min_level:
            status = f"🔒  Wymaga poziomu {skill.min_level}"
        else:
            status = f"💰  {skill.price} 🪙\n`^kup {skill.skill_id}`"

        # Stat requirements
        req_parts = []
        if skill.min_atk > 0:
            req_parts.append(f"ATK≥{skill.min_atk}")
        if skill.min_matk > 0:
            req_parts.append(f"MATK≥{skill.min_matk}")
        if skill.min_defense > 0:
            req_parts.append(f"DEF≥{skill.min_defense}")
        if skill.min_mdef > 0:
            req_parts.append(f"MDEF≥{skill.min_mdef}")
        if skill.min_spd > 0:
            req_parts.append(f"SPD≥{skill.min_spd}")
        req_text = " | ".join(req_parts) if req_parts else ""

        embed.add_field(
            name=f"{skill.emoji}  `{skill.skill_id}` — {skill.name}",
            value=f"{skill.description}\n{status}" + (f"\n📊 {req_text}" if req_text else ""),
            inline=False,
        )

    embed.set_footer(text="^sprzedaj <id>  ·  ^portfel  ·  ^deck")
    return embed


def _calculate_engagement_score(content: str) -> tuple[int, int]:
    """
    Calculate message engagement score.
    Returns (message_length, unique_words).
    """
    # Strip Discord formatting
    clean = re.sub(r'<[^>]+>', '', content)   # remove mentions, emojis
    clean = re.sub(r'https?://\S+', '', clean)  # remove URLs
    clean = clean.strip()

    msg_length = len(clean)
    words = set(clean.lower().split())
    unique_words = len(words)

    return msg_length, unique_words


# ──────────────────── Cog ────────────────────


class ActivityCog(commands.Cog, name="PvP Activity"):
    """Cog obsługujący aktywność, sklep i deck."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._voice_tracker: dict[int, float] = {}  # user_id -> last_reward_time
        self.voice_reward_loop.start()

    def cog_unload(self) -> None:
        self.voice_reward_loop.cancel()

    # ──────────────── Message Activity Listener ────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Track message activity and award XP/gold."""
        if message.author.bot:
            return
        if not message.guild:
            return
        # Ignore bot commands
        if message.content.startswith("^"):
            return

        db = await get_db()
        user_id = message.author.id

        # Anti-spam: cooldown check
        can_reward = await db.can_reward_message(user_id)
        if not can_reward:
            return

        # Calculate engagement
        msg_length, unique_words = _calculate_engagement_score(message.content)

        # Skip very short messages (anti-spam)
        if msg_length < MIN_MESSAGE_LENGTH:
            return

        # Get player data for prestige bonus
        player = await db.get_or_create_player(user_id, name=message.author.display_name)
        prestige = player.get("prestige_tier", 0)

        # Calculate rewards
        xp, gold = calculate_message_rewards(msg_length, unique_words, prestige)

        if xp <= 0 and gold <= 0:
            return

        # Award XP and gold
        level_info = await db.add_xp(user_id, xp)
        await db.add_gold(user_id, gold)

        # Record activity
        await db.record_message_reward(
            user_id=user_id,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            msg_length=msg_length,
            unique_words=unique_words,
            xp=xp,
            gold=gold,
        )

        # Level up notification
        if level_info["levels_gained"] > 0:
            embed = discord.Embed(
                title="🎉 Awans!",
                description=(
                    f"**{message.author.display_name}** awansuje na "
                    f"poziom **{level_info['new_level']}**!\n"
                    f"🎯 Otrzymujesz **{level_info['stat_points_gained']}** punktów statystyk.\n"
                    f"Użyj `^staty` aby je przydzielić."
                ),
                color=0x2ECC71,
            )
            await message.channel.send(embed=embed)

    # ──────────────── Voice Activity Loop ────────────────

    @tasks.loop(seconds=60)
    async def voice_reward_loop(self) -> None:
        """Periodically reward users in voice channels."""
        db = await get_db()
        now = time.time()

        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    # Check if enough time passed
                    last = self._voice_tracker.get(member.id, 0)
                    if now - last < VOICE_REWARD_INTERVAL:
                        continue

                    self._voice_tracker[member.id] = now

                    player = await db.get_or_create_player(member.id, name=member.display_name)
                    prestige = player.get("prestige_tier", 0)
                    tier_data = get_prestige_tier_data(prestige)

                    xp = int(VOICE_XP_PER_MINUTE * (1 + tier_data["xp_bonus"]))
                    gold = VOICE_GOLD_PER_MINUTE + tier_data["gold_per_msg_bonus"]

                    await db.add_xp(member.id, xp)
                    await db.add_gold(member.id, gold)
                    await db.record_voice_reward(member.id, guild.id, xp, gold)

    @voice_reward_loop.before_loop
    async def before_voice_loop(self) -> None:
        await self.bot.wait_until_ready()

    # ──────────────── Deck Commands ────────────────

    @commands.command(name="deck")
    async def deck(self, ctx: commands.Context) -> None:
        """Wyświetl swój deck (5 slotów skilli do walki)."""
        embed = await _build_deck_embed(ctx.author.id, ctx.author.display_name)
        view = DeckView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    # ──────────────── Shop Commands ────────────────

    @commands.command(name="sklep")
    async def shop(self, ctx: commands.Context, page: int = 1) -> None:
        """Wyświetl sklep umiejętności."""
        page = max(1, page)
        embed = await _build_shop_embed(ctx.author.id, page)
        view = ShopView(ctx.author.id, page)
        await view.update_page_indicator()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="kup")
    async def buy_skill(self, ctx: commands.Context, skill_id: str) -> None:
        """Kup skill ze sklepu. Użycie: ^kup <id>"""
        skill = get_skill(skill_id.lower())
        if not skill:
            await ctx.send(f"❌ Nie znaleziono skilla `{skill_id}`. Sprawdź `^sklep`.")
            return

        db = await get_db()
        player = await db.get_or_create_player(ctx.author.id, name=ctx.author.display_name)
        owned = await db.get_player_skills(ctx.author.id)

        if skill_id.lower() in owned:
            await ctx.send(f"✅ Już posiadasz **{skill.name}**!")
            return

        if player["level"] < skill.min_level:
            await ctx.send(f"🔒 **{skill.name}** wymaga poziomu **{skill.min_level}**. Twój poziom: **{player['level']}**.")
            return

        if player["gold"] < skill.price:
            await ctx.send(
                f"💰 Nie stać cię na **{skill.name}**! "
                f"Potrzebujesz **{skill.price}** 🪙, masz **{player['gold']}** 🪙."
            )
            return

        # Purchase
        await db.add_gold(ctx.author.id, -skill.price)
        await db.add_skill(ctx.author.id, skill.skill_id)

        embed = discord.Embed(
            title=f"{skill.emoji} Zakupiono: {skill.name}!",
            description=(
                f"{skill.description}\n\n"
                f"💰 Zapłacono: **{skill.price}** 🪙\n"
                f"Użyj `^deck` aby dodać do decku."
            ),
            color=0x2ECC71,
        )
        await ctx.send(embed=embed)

    @commands.command(name="sprzedaj")
    async def sell_skill(self, ctx: commands.Context, skill_id: str) -> None:
        """Sprzedaj skill. Użycie: ^sprzedaj <id>"""
        skill = get_skill(skill_id.lower())
        if not skill:
            await ctx.send(f"❌ Nie znaleziono skilla `{skill_id}`.")
            return

        db = await get_db()
        owned = await db.get_player_skills(ctx.author.id)

        if skill_id.lower() not in owned:
            await ctx.send(f"❌ Nie posiadasz **{skill.name}**!")
            return

        sell_price = skill.price // 2  # 50% refund
        await db.remove_skill(ctx.author.id, skill.skill_id)
        await db.add_gold(ctx.author.id, sell_price)

        # Remove from deck if equipped
        deck = await db.get_deck(ctx.author.id)
        new_deck = [s for s in deck if s != skill.skill_id]
        await db.set_deck(ctx.author.id, new_deck)

        embed = discord.Embed(
            title=f"💸 Sprzedano: {skill.name}",
            description=f"Otrzymano: **{sell_price}** 🪙 (50% wartości)",
            color=0xE74C3C,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ActivityCog(bot))
