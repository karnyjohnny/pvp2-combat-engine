"""
profile_cog.py — Cog 3: Profile, wallet, prestige, stat allocation.

Commands:
    ^pvpprofil [@user]  — show player profile
    ^portfel            — show wallet (gold, level, XP)
    ^prestiz            — prestige reset
    ^staty              — allocate stat points
"""

from __future__ import annotations

import discord
from discord.ext import commands

from pvp2.balance import (
    ATK_PER_POINT,
    DEF_PER_POINT,
    HP_PER_POINT,
    LUCK_PER_POINT,
    MATK_PER_POINT,
    MAX_LEVEL,
    MDEF_PER_POINT,
    SPD_PER_POINT,
    STAT_POINTS_PER_LEVEL,
    get_prestige_tier_data,
    xp_for_level,
)
from pvp2.db import get_db


# ──────────────────── Stat Allocation View ────────────────────


class StatAllocView(discord.ui.View):
    """Interactive stat allocation buttons."""

    STAT_INFO = {
        "hp": ("❤️ HP", HP_PER_POINT, "Punkty życia"),
        "atk": ("⚔️ ATK", ATK_PER_POINT, "Atak fizyczny"),
        "matk": ("✨ MATK", MATK_PER_POINT, "Atak magiczny"),
        "defense": ("🛡️ DEF", DEF_PER_POINT, "Obrona fizyczna"),
        "mdef": ("🔮 MDEF", MDEF_PER_POINT, "Obrona magiczna"),
        "spd": ("💨 SPD", SPD_PER_POINT, "Szybkość"),
        "luck": ("🍀 LUCK", LUCK_PER_POINT, "Szczęście"),
    }

    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=120)
        self.user_id = user_id

        for stat_name, (label, per_point, _desc) in self.STAT_INFO.items():
            button = discord.ui.Button(
                label=f"{label} (+{per_point})",
                style=discord.ButtonStyle.primary,
                custom_id=f"stat_alloc_{stat_name}",
            )
            button.callback = self._make_callback(stat_name)
            self.add_item(button)

    def _make_callback(self, stat_name: str):
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("To nie twój profil!", ephemeral=True)
                return

            db = await get_db()
            success = await db.allocate_stat(self.user_id, stat_name)

            if not success:
                player = await db.get_or_create_player(self.user_id)
                if player["available_stat_points"] <= 0:
                    await interaction.response.send_message(
                        "❌ Brak dostępnych punktów statystyk!", ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "❌ Nie można przydzielić punktu.", ephemeral=True,
                    )
                return

            # Refresh the stat display
            embed = await _build_stat_embed(self.user_id, interaction.user.display_name)
            player = await db.get_or_create_player(self.user_id)

            # Disable buttons if no more points
            if player["available_stat_points"] <= 0:
                for child in self.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        return callback


# ──────────────────── Helper Functions ────────────────────


async def _build_profile_embed(user_id: int, display_name: str) -> discord.Embed:
    """Build player profile embed."""
    db = await get_db()
    player = await db.get_or_create_player(user_id, name=display_name)
    owned_skills = await db.get_player_skills(user_id)
    prestige = player.get("prestige_tier", 0)
    tier_data = get_prestige_tier_data(prestige)

    # Prestige badge
    if prestige > 0:
        badge = f"{tier_data['emoji']} Prestiż {prestige} — {tier_data['name']}"
    else:
        badge = "Brak prestiżu"

    # Color based on prestige
    color = tier_data.get("color", 0x808080) if prestige > 0 else 0x3498DB

    # XP bar
    current_xp = player["xp"]
    needed_xp = xp_for_level(player["level"] + 1) if player["level"] < MAX_LEVEL else 0
    if needed_xp > 0:
        xp_pct = min(100, int(current_xp / needed_xp * 100))
        xp_bar_len = 10
        filled = int(xp_pct / 100 * xp_bar_len)
        xp_bar = "█" * filled + "░" * (xp_bar_len - filled)
        xp_text = f"`{xp_bar}` {current_xp}/{needed_xp} ({xp_pct}%)"
    else:
        xp_text = "MAX LEVEL ✨"

    # Win rate
    total = player["total_battles"]
    wins = player["total_wins"]
    winrate = f"{(wins / total * 100):.0f}%" if total > 0 else "N/A"

    embed = discord.Embed(
        title=f"👤 Profil — {display_name}",
        description=badge,
        color=color,
    )

    embed.add_field(
        name="📊 Ogólne",
        value=(
            f"📏 Poziom: **{player['level']}** / {MAX_LEVEL}\n"
            f"📈 XP: {xp_text}\n"
            f"💰 Złoto: **{player['gold']}** 🪙\n"
            f"🎴 Skille: **{len(owned_skills)}**"
        ),
        inline=True,
    )

    embed.add_field(
        name="⚔️ Walki",
        value=(
            f"🎮 Łącznie: **{total}**\n"
            f"🏆 Wygrane: **{wins}**\n"
            f"📊 Winrate: **{winrate}**"
        ),
        inline=True,
    )

    embed.add_field(
        name="📋 Statystyki",
        value=(
            f"❤️ HP: **{player['max_hp']}**\n"
            f"⚔️ ATK: **{player['atk']}**\n"
            f"✨ MATK: **{player['matk']}**\n"
            f"🛡️ DEF: **{player['defense']}**\n"
            f"🔮 MDEF: **{player['mdef']}**\n"
            f"💨 SPD: **{player['spd']}**\n"
            f"🍀 LUCK: **{player['luck']}**\n"
            f"🎯 ACC: **{player['accuracy']}**\n"
            f"💨 EVA: **{player['evasion']}**\n"
            f"💥 CRIT: **{player['crit_chance']:.0f}%**\n"
            f"💥 CRIT DMG: **{player['crit_dmg']:.0f}%**"
        ),
        inline=False,
    )

    if prestige > 0:
        embed.add_field(
            name="🌟 Bonusy Prestiżu",
            value=(
                f"📈 XP bonus: **+{int(tier_data['xp_bonus'] * 100)}%**\n"
                f"💰 Gold/msg: **+{tier_data['gold_per_msg_bonus']}** 🪙\n"
                f"❤️ HP: **+{tier_data['flat_hp']}**\n"
                f"⚔️ ATK: **+{tier_data['flat_atk']}**\n"
                f"✨ MATK: **+{tier_data['flat_matk']}**"
            ),
            inline=False,
        )

    if player["available_stat_points"] > 0:
        embed.set_footer(
            text=f"🔔 Masz {player['available_stat_points']} punktów statystyk! Użyj ^staty"
        )

    return embed


async def _build_stat_embed(user_id: int, display_name: str) -> discord.Embed:
    """Build stat allocation embed."""
    db = await get_db()
    player = await db.get_or_create_player(user_id)

    embed = discord.Embed(
        title=f"📊 Statystyki — {display_name}",
        description=f"Dostępne punkty: **{player['available_stat_points']}**\nKliknij przycisk, aby przydzielić 1 punkt.",
        color=0x3498DB,
    )

    stats_text = (
        f"❤️ HP: **{player['max_hp']}** (+{HP_PER_POINT}/pkt)\n"
        f"⚔️ ATK: **{player['atk']}** (+{ATK_PER_POINT}/pkt)\n"
        f"✨ MATK: **{player['matk']}** (+{MATK_PER_POINT}/pkt)\n"
        f"🛡️ DEF: **{player['defense']}** (+{DEF_PER_POINT}/pkt)\n"
        f"🔮 MDEF: **{player['mdef']}** (+{MDEF_PER_POINT}/pkt)\n"
        f"💨 SPD: **{player['spd']}** (+{SPD_PER_POINT}/pkt)\n"
        f"🍀 LUCK: **{player['luck']}** (+{LUCK_PER_POINT}/pkt)"
    )

    embed.add_field(name="Aktualne statystyki", value=stats_text, inline=False)
    return embed


async def _build_wallet_embed(user_id: int, display_name: str) -> discord.Embed:
    """Build wallet embed."""
    db = await get_db()
    player = await db.get_or_create_player(user_id, name=display_name)
    prestige = player.get("prestige_tier", 0)
    tier_data = get_prestige_tier_data(prestige)

    current_xp = player["xp"]
    needed_xp = xp_for_level(player["level"] + 1) if player["level"] < MAX_LEVEL else 0

    embed = discord.Embed(
        title=f"💰 Portfel — {display_name}",
        color=0xF39C12,
    )

    embed.add_field(
        name="💰 Złoto",
        value=f"**{player['gold']}** 🪙",
        inline=True,
    )

    embed.add_field(
        name="📏 Poziom",
        value=f"**{player['level']}** / {MAX_LEVEL}",
        inline=True,
    )

    embed.add_field(
        name="📈 XP",
        value=f"**{current_xp}** / **{needed_xp}**" if needed_xp > 0 else "MAX ✨",
        inline=True,
    )

    if prestige > 0:
        embed.add_field(
            name="🌟 Prestiż",
            value=f"{tier_data['emoji']} Tier **{prestige}** — {tier_data['name']}",
            inline=False,
        )

    return embed


# ──────────────────── Cog ────────────────────


class ProfileCog(commands.Cog, name="PvP Profile"):
    """Cog obsługujący profil, portfel, prestiż i statystyki."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="pvpprofil")
    async def profile(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """Wyświetl profil PvP. Użycie: ^pvpprofil [@gracz]"""
        target = member or ctx.author
        embed = await _build_profile_embed(target.id, target.display_name)
        await ctx.send(embed=embed)

    @commands.command(name="portfel")
    async def wallet(self, ctx: commands.Context) -> None:
        """Wyświetl swój portfel (złoto, poziom, XP)."""
        embed = await _build_wallet_embed(ctx.author.id, ctx.author.display_name)
        await ctx.send(embed=embed)

    @commands.command(name="staty")
    async def allocate_stats(self, ctx: commands.Context) -> None:
        """Przydziel punkty statystyk. Interaktywne przyciski."""
        db = await get_db()
        player = await db.get_or_create_player(ctx.author.id, name=ctx.author.display_name)

        if player["available_stat_points"] <= 0:
            await ctx.send("❌ Nie masz dostępnych punktów statystyk! Zdobądź je awansując na wyższy poziom.")
            return

        embed = await _build_stat_embed(ctx.author.id, ctx.author.display_name)
        view = StatAllocView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="prestiz")
    async def prestige(self, ctx: commands.Context) -> None:
        """
        Wykonaj prestiż! Resetuje poziom, statystyki i skille,
        ale daje permanentne bonusy.
        """
        db = await get_db()
        player = await db.get_or_create_player(ctx.author.id, name=ctx.author.display_name)
        next_tier = player["prestige_tier"] + 1
        tier_data = get_prestige_tier_data(next_tier)

        if player["level"] < tier_data["min_level"]:
            embed = discord.Embed(
                title="🌟 Prestiż",
                description=(
                    f"Aby wykonać prestiż **{next_tier}** ({tier_data['emoji']} {tier_data['name']}), "
                    f"potrzebujesz poziomu **{tier_data['min_level']}**.\n"
                    f"Twój obecny poziom: **{player['level']}**."
                ),
                color=0xE74C3C,
            )
            await ctx.send(embed=embed)
            return

        # Confirmation
        embed = discord.Embed(
            title=f"🌟 Prestiż {next_tier} — {tier_data['emoji']} {tier_data['name']}",
            description=(
                "**⚠️ UWAGA! Prestiż zresetuje:**\n"
                "• Poziom → 1, XP → 0\n"
                "• Wszystkie statystyki → bazowe\n"
                "• Punkty statystyk → 0\n"
                "• **Wszystkie skille** (kolekcja + deck)\n\n"
                "**🎁 Otrzymasz permanentnie:**\n"
                f"• 📈 XP bonus: **+{int(tier_data['xp_bonus'] * 100)}%**\n"
                f"• 💰 Gold/msg: **+{tier_data['gold_per_msg_bonus']}** 🪙\n"
                f"• ❤️ HP: **+{tier_data['flat_hp']}**\n"
                f"• ⚔️ ATK: **+{tier_data['flat_atk']}**\n"
                f"• ✨ MATK: **+{tier_data['flat_matk']}**\n"
                f"• 💰 Startowe złoto: **{tier_data['start_gold']}** 🪙\n\n"
                "**Czy na pewno chcesz wykonać prestiż?**"
            ),
            color=tier_data.get("color", 0xFFD700),
        )

        view = PrestigeConfirmView(ctx.author.id)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        if view.confirmed:
            result = await db.prestige(ctx.author.id)
            if result["success"]:
                embed = discord.Embed(
                    title=f"🌟 Prestiż {result['new_tier']} — Osiągnięty!",
                    description=(
                        f"{tier_data['emoji']} Gratulacje **{ctx.author.display_name}**!\n\n"
                        f"Twoje konto zostało zresetowane z bonusami prestiżu.\n"
                        f"💰 Startowe złoto: **{result['start_gold']}** 🪙\n\n"
                        f"Powodzenia w nowej przygodzie! 🎮"
                    ),
                    color=tier_data.get("color", 0xFFD700),
                )
                await msg.edit(embed=embed, view=None)
            else:
                await msg.edit(
                    content=f"❌ Nie spełniasz wymagań (wymagany poziom: {result.get('required_level', '?')}).",
                    view=None,
                )
        else:
            await msg.edit(content="❌ Prestiż anulowany.", embed=None, view=None)


class PrestigeConfirmView(discord.ui.View):
    """Confirmation view for prestige."""

    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=60)
        self.user_id = user_id
        self.confirmed = False

    @discord.ui.button(label="✅ Tak, wykonaj prestiż!", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("To nie twój prestiż!", ephemeral=True)
            return
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="❌ Anuluj", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("To nie twój prestiż!", ephemeral=True)
            return
        self.confirmed = False
        await interaction.response.defer()
        self.stop()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
