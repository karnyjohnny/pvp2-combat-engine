"""
skills.py — 32 skill definitions for the PvP2 combat engine.

Each skill is an object with effects, stat requirements, costs, and cooldowns.
No if/elif chains — skills are looked up by ID from a registry dict.

Categories:
    Fire (4), Ice (4), Lightning (4), Dark (4), Holy (4),
    Physical (4), Support (4), Ultimate (4)
"""

from __future__ import annotations

from pvp2 import effects as fx
from pvp2.models import (
    Element, ResourceType, Skill, SkillEffect, StatusType, TargetType,
)

# ══════════════════════════════════════════════════════════════
#  FIRE SKILLS (4)
# ══════════════════════════════════════════════════════════════

fireball = Skill(
    skill_id="fireball",
    name="Kula Ognia",
    description="Eksploduje przy trafieniu i może podpalić cel.",
    emoji="🔥",
    element=Element.FIRE,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=40, element=Element.FIRE,
            scaling_stat="matk", scaling_ratio=1.2,
        ),
        SkillEffect(
            effect_type="apply_status", chance=40.0,
            status_to_apply=fx.make_burn(duration=3, tick_damage=15),
        ),
    ],
    cooldown=0,
    resource_type=ResourceType.MANA,
    resource_cost=15,
    action_cost=100,
    min_matk=20,
    min_level=1,
    price=150,
    category="Ogień",
)

inferno = Skill(
    skill_id="inferno",
    name="Piekło",
    description="Fala ognia ogarnia wszystkich wrogów.",
    emoji="🌋",
    element=Element.FIRE,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=30, element=Element.FIRE,
            scaling_stat="matk", scaling_ratio=0.9,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=30.0,
            status_to_apply=fx.make_burn(duration=2, tick_damage=12),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.MANA,
    resource_cost=35,
    action_cost=120,
    min_matk=35,
    min_level=5,
    price=300,
    category="Ogień",
)

fire_shield = Skill(
    skill_id="fire_shield",
    name="Ognista Tarcza",
    description="Otacza się tarczą ognia, odbijając część obrażeń.",
    emoji="🔥🛡️",
    element=Element.FIRE,
    target_type=TargetType.SELF,
    effects=[
        SkillEffect(
            effect_type="shield", power=80,
            target=TargetType.SELF,
            status_to_apply=fx.make_shield(amount=80, duration=3),
        ),
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.SELF,
            status_to_apply=fx.make_reflect(duration=3, power=15),
        ),
    ],
    cooldown=4,
    resource_type=ResourceType.MANA,
    resource_cost=25,
    action_cost=90,
    min_matk=25,
    min_level=3,
    price=250,
    category="Ogień",
)

meteor = Skill(
    skill_id="meteor",
    name="Meteor",
    description="Sprowadza meteor z nieba — potężne obrażenia AoE.",
    emoji="☄️",
    element=Element.FIRE,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=70, element=Element.FIRE,
            scaling_stat="matk", scaling_ratio=1.5,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=25.0,
            status_to_apply=fx.make_stun(duration=1, chance=25),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=5,
    resource_type=ResourceType.MANA,
    resource_cost=50,
    action_cost=150,
    is_ultimate=True,
    min_matk=50,
    min_level=10,
    price=500,
    category="Ogień",
)

# ══════════════════════════════════════════════════════════════
#  ICE SKILLS (4)
# ══════════════════════════════════════════════════════════════

ice_lance = Skill(
    skill_id="ice_lance",
    name="Włócznia Lodu",
    description="Przeszywa wroga lodem, szansa na zamrożenie.",
    emoji="🧊",
    element=Element.ICE,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=45, element=Element.ICE,
            scaling_stat="matk", scaling_ratio=1.1,
        ),
        SkillEffect(
            effect_type="apply_status", chance=25.0,
            status_to_apply=fx.make_freeze(duration=1, tick_damage=8),
        ),
    ],
    cooldown=0,
    resource_type=ResourceType.MANA,
    resource_cost=15,
    action_cost=95,
    min_matk=20,
    min_level=1,
    price=150,
    category="Lód",
)

blizzard = Skill(
    skill_id="blizzard",
    name="Zamieć",
    description="Pokrywa pole bitwy lodem — obrażenia AoE + spowolnienie.",
    emoji="🌨️",
    element=Element.ICE,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=35, element=Element.ICE,
            scaling_stat="matk", scaling_ratio=0.85,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=40.0,
            status_to_apply=fx.make_slow(duration=2, power=0.25),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.MANA,
    resource_cost=35,
    action_cost=120,
    min_matk=40,
    min_level=6,
    price=350,
    category="Lód",
)

frozen_armor = Skill(
    skill_id="frozen_armor",
    name="Lodowa Zbroja",
    description="Tarcza z lodu zwiększa obronę i spowalnia atakujących.",
    emoji="🧊🛡️",
    element=Element.ICE,
    target_type=TargetType.SELF,
    effects=[
        SkillEffect(
            effect_type="shield", power=100,
            target=TargetType.SELF,
            status_to_apply=fx.make_shield(amount=100, duration=3),
        ),
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.SELF,
            status_to_apply=fx.make_def_buff(duration=3, power=0.2),
        ),
    ],
    cooldown=4,
    resource_type=ResourceType.MANA,
    resource_cost=25,
    action_cost=90,
    min_mdef=20,
    min_level=3,
    price=250,
    category="Lód",
)

absolute_zero = Skill(
    skill_id="absolute_zero",
    name="Absolutne Zero",
    description="Zamraża wszystko — ogromne obrażenia + zamrożenie.",
    emoji="❄️",
    element=Element.ICE,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=60, element=Element.ICE,
            scaling_stat="matk", scaling_ratio=1.4,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=35.0,
            status_to_apply=fx.make_freeze(duration=2, tick_damage=10),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=5,
    resource_type=ResourceType.MANA,
    resource_cost=50,
    action_cost=150,
    is_ultimate=True,
    min_matk=55,
    min_level=12,
    price=550,
    category="Lód",
)

# ══════════════════════════════════════════════════════════════
#  LIGHTNING SKILLS (4)
# ══════════════════════════════════════════════════════════════

thunder_strike = Skill(
    skill_id="thunder_strike",
    name="Uderzenie Gromu",
    description="AoE błyskawice + porażenie wrogów.",
    emoji="⚡",
    element=Element.LIGHTNING,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=35, element=Element.LIGHTNING,
            scaling_stat="matk", scaling_ratio=1.0,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=35.0,
            status_to_apply=fx.make_shock(duration=2),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=2,
    resource_type=ResourceType.MANA,
    resource_cost=25,
    action_cost=110,
    min_matk=25,
    min_level=3,
    price=250,
    category="Błyskawica",
)

chain_lightning = Skill(
    skill_id="chain_lightning",
    name="Łańcuch Błyskawic",
    description="Błyskawica przeskakuje między wrogami.",
    emoji="⚡⚡",
    element=Element.LIGHTNING,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=25, element=Element.LIGHTNING,
            scaling_stat="matk", scaling_ratio=0.8,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=20.0,
            status_to_apply=fx.make_shock(duration=1),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=2,
    resource_type=ResourceType.MANA,
    resource_cost=30,
    action_cost=100,
    min_matk=30,
    min_level=4,
    price=300,
    category="Błyskawica",
)

static_shield = Skill(
    skill_id="static_shield",
    name="Pole Elektrostatyczne",
    description="Tarcza elektryczna — absorbuje i razi atakujących.",
    emoji="⚡🛡️",
    element=Element.LIGHTNING,
    target_type=TargetType.SELF,
    effects=[
        SkillEffect(
            effect_type="shield", power=70,
            target=TargetType.SELF,
            status_to_apply=fx.make_shield(amount=70, duration=3),
        ),
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.SELF,
            status_to_apply=fx.make_reflect(duration=3, power=10),
        ),
    ],
    cooldown=4,
    resource_type=ResourceType.MANA,
    resource_cost=20,
    action_cost=85,
    min_matk=20,
    min_level=2,
    price=200,
    category="Błyskawica",
)

storm = Skill(
    skill_id="storm",
    name="Burza",
    description="Wywołuje burzę — potężne AoE + ogłuszenie.",
    emoji="🌩️",
    element=Element.LIGHTNING,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=65, element=Element.LIGHTNING,
            scaling_stat="matk", scaling_ratio=1.3,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=30.0,
            status_to_apply=fx.make_stun(duration=1, chance=30),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=5,
    resource_type=ResourceType.MANA,
    resource_cost=50,
    action_cost=140,
    is_ultimate=True,
    min_matk=50,
    min_level=10,
    price=500,
    category="Błyskawica",
)

# ══════════════════════════════════════════════════════════════
#  DARK SKILLS (4)
# ══════════════════════════════════════════════════════════════

shadow_bolt = Skill(
    skill_id="shadow_bolt",
    name="Pocisk Mroku",
    description="Mroczna energia uderza we wroga, osłabiając obronę.",
    emoji="💀",
    element=Element.DARK,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=42, element=Element.DARK,
            scaling_stat="matk", scaling_ratio=1.15,
        ),
        SkillEffect(
            effect_type="apply_status", chance=35.0,
            status_to_apply=fx.make_def_debuff(duration=2, power=0.15),
        ),
    ],
    cooldown=0,
    resource_type=ResourceType.MANA,
    resource_cost=15,
    action_cost=100,
    min_matk=20,
    min_level=1,
    price=150,
    category="Mrok",
)

death_spiral = Skill(
    skill_id="death_spiral",
    name="Spirala Śmierci",
    description="Wyrywa esencję życia — obrażenia + kradzież HP.",
    emoji="💀🌀",
    element=Element.DARK,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=50, element=Element.DARK,
            scaling_stat="matk", scaling_ratio=1.2,
        ),
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.SELF,
            status_to_apply=fx.make_lifesteal(duration=2, power=25),
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.MANA,
    resource_cost=30,
    action_cost=110,
    min_matk=35,
    min_level=5,
    price=350,
    category="Mrok",
)

curse = Skill(
    skill_id="curse",
    name="Klątwa",
    description="Przeklina wroga — zatrucie + uciszenie.",
    emoji="🔮",
    element=Element.DARK,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="apply_status", chance=50.0,
            status_to_apply=fx.make_poison(duration=4, tick_damage=10),
        ),
        SkillEffect(
            effect_type="apply_status", chance=30.0,
            status_to_apply=fx.make_silence(duration=2),
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.MANA,
    resource_cost=25,
    action_cost=95,
    min_matk=30,
    min_level=4,
    price=300,
    category="Mrok",
)

apocalypse = Skill(
    skill_id="apocalypse",
    name="Apokalipsa",
    description="Mroczna fala pochłania wszystko — masowe obrażenia.",
    emoji="🌑",
    element=Element.DARK,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=75, element=Element.DARK,
            scaling_stat="matk", scaling_ratio=1.5,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=25.0,
            status_to_apply=fx.make_silence(duration=2, chance=25),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=6,
    resource_type=ResourceType.MANA,
    resource_cost=55,
    action_cost=160,
    is_ultimate=True,
    min_matk=55,
    min_level=12,
    price=600,
    category="Mrok",
)

# ══════════════════════════════════════════════════════════════
#  HOLY SKILLS (4)
# ══════════════════════════════════════════════════════════════

holy_light = Skill(
    skill_id="holy_light",
    name="Święte Światło",
    description="Leczy sojusznika świętą energią.",
    emoji="✨",
    element=Element.HOLY,
    target_type=TargetType.SINGLE_ALLY,
    effects=[
        SkillEffect(
            effect_type="heal", power=60,
            scaling_stat="matk", scaling_ratio=1.3,
            target=TargetType.SINGLE_ALLY,
        ),
    ],
    cooldown=1,
    resource_type=ResourceType.MANA,
    resource_cost=20,
    action_cost=90,
    min_matk=25,
    min_level=2,
    price=200,
    category="Światło",
)

smite = Skill(
    skill_id="smite",
    name="Kara Boska",
    description="Święta moc uderza we wroga — bonus vs. nieumarli.",
    emoji="⚡✨",
    element=Element.HOLY,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=48, element=Element.HOLY,
            scaling_stat="matk", scaling_ratio=1.2,
        ),
    ],
    cooldown=1,
    resource_type=ResourceType.MANA,
    resource_cost=20,
    action_cost=100,
    min_matk=25,
    min_level=2,
    price=200,
    category="Światło",
)

divine_shield = Skill(
    skill_id="divine_shield",
    name="Boska Tarcza",
    description="Potężna tarcza ochronna + oczyszczenie debuffów.",
    emoji="🛡️✨",
    element=Element.HOLY,
    target_type=TargetType.SINGLE_ALLY,
    effects=[
        SkillEffect(
            effect_type="shield", power=120,
            target=TargetType.SINGLE_ALLY,
            status_to_apply=fx.make_shield(amount=120, duration=3),
        ),
        SkillEffect(
            effect_type="remove_status",
            target=TargetType.SINGLE_ALLY,
            description="Oczyszcza 2 debuffy.",
        ),
    ],
    cooldown=4,
    resource_type=ResourceType.MANA,
    resource_cost=30,
    action_cost=95,
    min_matk=30,
    min_mdef=20,
    min_level=5,
    price=350,
    category="Światło",
)

judgment = Skill(
    skill_id="judgment",
    name="Sąd Ostateczny",
    description="Boskie światło uderza we wszystkich wrogów + leczenie drużyny.",
    emoji="☀️",
    element=Element.HOLY,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=55, element=Element.HOLY,
            scaling_stat="matk", scaling_ratio=1.3,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="heal", power=30,
            scaling_stat="matk", scaling_ratio=0.5,
            target=TargetType.ALL_ALLIES,
        ),
    ],
    cooldown=5,
    resource_type=ResourceType.MANA,
    resource_cost=50,
    action_cost=140,
    is_ultimate=True,
    min_matk=50,
    min_level=10,
    price=500,
    category="Światło",
)

# ══════════════════════════════════════════════════════════════
#  PHYSICAL SKILLS (4)
# ══════════════════════════════════════════════════════════════

slash = Skill(
    skill_id="slash",
    name="Cięcie",
    description="Szybkie cięcie mieczem — szansa na krwawienie.",
    emoji="⚔️",
    element=Element.PHYSICAL,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=35, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.2,
        ),
        SkillEffect(
            effect_type="apply_status", chance=30.0,
            status_to_apply=fx.make_bleed(duration=3, tick_damage=10),
        ),
    ],
    cooldown=0,
    resource_type=ResourceType.ENERGY,
    resource_cost=10,
    action_cost=85,
    min_atk=15,
    min_level=1,
    price=100,
    category="Fizyczne",
)

cleave = Skill(
    skill_id="cleave",
    name="Rozcięcie",
    description="Potężne cięcie ogarniające wielu wrogów.",
    emoji="⚔️💨",
    element=Element.PHYSICAL,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=30, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=0.9,
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=2,
    resource_type=ResourceType.ENERGY,
    resource_cost=20,
    action_cost=110,
    min_atk=25,
    min_level=3,
    price=200,
    category="Fizyczne",
)

shield_bash = Skill(
    skill_id="shield_bash",
    name="Uderzenie Tarczą",
    description="Ogłuszające uderzenie tarczą — obrażenia + stun.",
    emoji="🛡️💥",
    element=Element.PHYSICAL,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=30, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=0.8,
        ),
        SkillEffect(
            effect_type="apply_status", chance=40.0,
            status_to_apply=fx.make_stun(duration=1, chance=40),
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.ENERGY,
    resource_cost=15,
    action_cost=100,
    min_atk=20,
    min_defense=15,
    min_level=2,
    price=200,
    category="Fizyczne",
)

backstab = Skill(
    skill_id="backstab",
    name="Cios w Plecy",
    description="Podstępny atak z zaskoczenia — wysoki crit, szansa na zatrucie.",
    emoji="🗡️",
    element=Element.PHYSICAL,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=55, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.4,
        ),
        SkillEffect(
            effect_type="apply_status", chance=35.0,
            status_to_apply=fx.make_poison(duration=3, tick_damage=8),
        ),
    ],
    cooldown=2,
    resource_type=ResourceType.ENERGY,
    resource_cost=20,
    action_cost=90,
    min_atk=30,
    min_spd=15,
    min_level=4,
    price=300,
    category="Fizyczne",
)

# ══════════════════════════════════════════════════════════════
#  SUPPORT SKILLS (4)
# ══════════════════════════════════════════════════════════════

war_cry = Skill(
    skill_id="war_cry",
    name="Okrzyk Wojenny",
    description="Dodaje haste i ATK buff całej drużynie.",
    emoji="📯",
    element=Element.PHYSICAL,
    target_type=TargetType.ALL_ALLIES,
    effects=[
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.ALL_ALLIES,
            status_to_apply=fx.make_haste(duration=2, power=0.2),
        ),
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.ALL_ALLIES,
            status_to_apply=fx.make_atk_buff(duration=2, power=0.15),
        ),
    ],
    cooldown=4,
    resource_type=ResourceType.RAGE,
    resource_cost=30,
    action_cost=90,
    min_atk=20,
    min_level=3,
    price=200,
    category="Wsparcie",
)

healing_wave = Skill(
    skill_id="healing_wave",
    name="Fala Leczenia",
    description="Leczy całą drużynę falą energii.",
    emoji="💚",
    element=Element.NATURE,
    target_type=TargetType.ALL_ALLIES,
    effects=[
        SkillEffect(
            effect_type="heal", power=35,
            scaling_stat="matk", scaling_ratio=0.8,
            target=TargetType.ALL_ALLIES,
        ),
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.ALL_ALLIES,
            status_to_apply=fx.make_regen(duration=2, tick_heal=10),
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.MANA,
    resource_cost=35,
    action_cost=100,
    min_matk=30,
    min_level=4,
    price=300,
    category="Wsparcie",
)

barrier = Skill(
    skill_id="barrier",
    name="Bariera",
    description="Tworzy ochronną barierę wokół sojusznika.",
    emoji="🔮🛡️",
    element=Element.ARCANE,
    target_type=TargetType.SINGLE_ALLY,
    effects=[
        SkillEffect(
            effect_type="shield", power=150,
            target=TargetType.SINGLE_ALLY,
            status_to_apply=fx.make_shield(amount=150, duration=3),
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.MANA,
    resource_cost=25,
    action_cost=90,
    min_matk=25,
    min_level=3,
    price=250,
    category="Wsparcie",
)

mass_purify = Skill(
    skill_id="mass_purify",
    name="Masowe Oczyszczenie",
    description="Usuwa wszystkie debuffy z drużyny + mały heal.",
    emoji="🌟",
    element=Element.HOLY,
    target_type=TargetType.ALL_ALLIES,
    effects=[
        SkillEffect(
            effect_type="remove_status",
            target=TargetType.ALL_ALLIES,
            description="Oczyszcza 3 debuffy z każdego sojusznika.",
        ),
        SkillEffect(
            effect_type="heal", power=20,
            scaling_stat="matk", scaling_ratio=0.4,
            target=TargetType.ALL_ALLIES,
        ),
    ],
    cooldown=4,
    resource_type=ResourceType.MANA,
    resource_cost=30,
    action_cost=95,
    min_matk=30,
    min_level=5,
    price=350,
    category="Wsparcie",
)

# ══════════════════════════════════════════════════════════════
#  ULTIMATE / SPECIAL SKILLS (4)
# ══════════════════════════════════════════════════════════════

dragon_breath = Skill(
    skill_id="dragon_breath",
    name="Oddech Smoka",
    description="Ogień smoka spala wszystkich wrogów.",
    emoji="🐉",
    element=Element.FIRE,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=80, element=Element.FIRE,
            scaling_stat="matk", scaling_ratio=1.6,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=50.0,
            status_to_apply=fx.make_burn(duration=3, tick_damage=20),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=6,
    resource_type=ResourceType.MANA,
    resource_cost=60,
    action_cost=160,
    is_ultimate=True,
    ultimate_charge_gain=0,
    min_matk=60,
    min_level=15,
    price=700,
    category="Ultimatum",
)

time_stop = Skill(
    skill_id="time_stop",
    name="Zatrzymanie Czasu",
    description="Zatrzymuje czas — ogłusza WSZYSTKICH wrogów + zyskujesz extra turę.",
    emoji="⏱️",
    element=Element.ARCANE,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="apply_status", chance=60.0,
            status_to_apply=fx.make_stun(duration=1, chance=60),
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="damage", power=25, element=Element.ARCANE,
            scaling_stat="matk", scaling_ratio=0.5,
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=6,
    resource_type=ResourceType.MANA,
    resource_cost=55,
    action_cost=50,  # low cost = almost instant extra turn
    is_ultimate=True,
    ultimate_charge_gain=0,
    min_matk=55,
    min_spd=20,
    min_level=15,
    price=700,
    category="Ultimatum",
)

arcane_explosion = Skill(
    skill_id="arcane_explosion",
    name="Wybuch Arkanowy",
    description="Skoncentrowana energia arkany — masowe obrażenia.",
    emoji="🔮",
    element=Element.ARCANE,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=70, element=Element.ARCANE,
            scaling_stat="matk", scaling_ratio=1.4,
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=4,
    resource_type=ResourceType.MANA,
    resource_cost=45,
    action_cost=130,
    min_matk=45,
    min_level=8,
    price=450,
    category="Arkana",
)

berserker_rage = Skill(
    skill_id="berserker_rage",
    name="Szał Berserkera",
    description="Wchodzi w szał — ogromny bonus ATK + lifesteal, ale traci DEF.",
    emoji="🔴",
    element=Element.PHYSICAL,
    target_type=TargetType.SELF,
    effects=[
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.SELF,
            status_to_apply=fx.make_atk_buff(duration=3, power=0.5),
        ),
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.SELF,
            status_to_apply=fx.make_lifesteal(duration=3, power=20),
        ),
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.SELF,
            status_to_apply=fx.make_def_debuff(duration=3, power=0.3, chance=100),
        ),
    ],
    cooldown=5,
    resource_type=ResourceType.RAGE,
    resource_cost=50,
    action_cost=80,
    min_atk=40,
    min_level=8,
    price=450,
    category="Fizyczne",
)

# ══════════════════════════════════════════════════════════════
#  NATURE / EXTRA SKILLS (4) — to reach 32
# ══════════════════════════════════════════════════════════════

vine_whip = Skill(
    skill_id="vine_whip",
    name="Bicz z Pnączy",
    description="Pnącza oplatają wroga — obrażenia + unieruchomienie.",
    emoji="🌿",
    element=Element.NATURE,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=38, element=Element.NATURE,
            scaling_stat="matk", scaling_ratio=1.1,
        ),
        SkillEffect(
            effect_type="apply_status", chance=35.0,
            status_to_apply=fx.make_immobilize(duration=1),
        ),
    ],
    cooldown=1,
    resource_type=ResourceType.MANA,
    resource_cost=15,
    action_cost=95,
    min_matk=20,
    min_level=2,
    price=150,
    category="Natura",
)

toxic_spores = Skill(
    skill_id="toxic_spores",
    name="Toksyczne Zarodniki",
    description="Rozpyla trujące zarodniki — AoE zatrucie.",
    emoji="🍄",
    element=Element.NATURE,
    target_type=TargetType.ALL_ENEMIES,
    effects=[
        SkillEffect(
            effect_type="damage", power=20, element=Element.NATURE,
            scaling_stat="matk", scaling_ratio=0.6,
            target=TargetType.ALL_ENEMIES,
        ),
        SkillEffect(
            effect_type="apply_status", chance=50.0,
            status_to_apply=fx.make_poison(duration=4, tick_damage=12),
            target=TargetType.ALL_ENEMIES,
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.MANA,
    resource_cost=25,
    action_cost=105,
    min_matk=25,
    min_level=4,
    price=250,
    category="Natura",
)

provoke = Skill(
    skill_id="provoke",
    name="Prowokacja",
    description="Wymusza ataki na siebie — taunt + tarcza.",
    emoji="🛡️😤",
    element=Element.PHYSICAL,
    target_type=TargetType.SELF,
    effects=[
        SkillEffect(
            effect_type="apply_status",
            target=TargetType.SELF,
            status_to_apply=fx.make_taunt(duration=2),
        ),
        SkillEffect(
            effect_type="shield", power=60,
            target=TargetType.SELF,
            status_to_apply=fx.make_shield(amount=60, duration=2),
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.RAGE,
    resource_cost=20,
    action_cost=85,
    min_defense=20,
    min_level=3,
    price=200,
    category="Obrona",
)

execute = Skill(
    skill_id="execute",
    name="Egzekucja",
    description="Potężny cios kończący — bonus obrażeń vs. cel z niskim HP.",
    emoji="⚰️",
    element=Element.PHYSICAL,
    target_type=TargetType.SINGLE_ENEMY,
    effects=[
        SkillEffect(
            effect_type="damage", power=70, element=Element.PHYSICAL,
            scaling_stat="atk", scaling_ratio=1.8,
            description="Bonus +50% obrażeń gdy cel < 30% HP.",
        ),
    ],
    cooldown=3,
    resource_type=ResourceType.RAGE,
    resource_cost=40,
    action_cost=110,
    min_atk=35,
    min_level=6,
    price=400,
    category="Fizyczne",
)


# ══════════════════════════════════════════════════════════════
#  SKILL REGISTRY
# ══════════════════════════════════════════════════════════════

ALL_SKILLS: dict[str, Skill] = {
    # Fire
    "fireball": fireball,
    "inferno": inferno,
    "fire_shield": fire_shield,
    "meteor": meteor,
    # Ice
    "ice_lance": ice_lance,
    "blizzard": blizzard,
    "frozen_armor": frozen_armor,
    "absolute_zero": absolute_zero,
    # Lightning
    "thunder_strike": thunder_strike,
    "chain_lightning": chain_lightning,
    "static_shield": static_shield,
    "storm": storm,
    # Dark
    "shadow_bolt": shadow_bolt,
    "death_spiral": death_spiral,
    "curse": curse,
    "apocalypse": apocalypse,
    # Holy
    "holy_light": holy_light,
    "smite": smite,
    "divine_shield": divine_shield,
    "judgment": judgment,
    # Physical
    "slash": slash,
    "cleave": cleave,
    "shield_bash": shield_bash,
    "backstab": backstab,
    # Support
    "war_cry": war_cry,
    "healing_wave": healing_wave,
    "barrier": barrier,
    "mass_purify": mass_purify,
    # Ultimate / Special
    "dragon_breath": dragon_breath,
    "time_stop": time_stop,
    "arcane_explosion": arcane_explosion,
    "berserker_rage": berserker_rage,
    # Nature / Extra
    "vine_whip": vine_whip,
    "toxic_spores": toxic_spores,
    "provoke": provoke,
    "execute": execute,
}


def get_skill(skill_id: str) -> Skill | None:
    """Look up a skill by ID."""
    return ALL_SKILLS.get(skill_id)


def get_skills_by_category(category: str) -> list[Skill]:
    """Get all skills in a category."""
    return [s for s in ALL_SKILLS.values() if s.category == category]


def get_all_categories() -> list[str]:
    """Get all unique skill categories."""
    return sorted(set(s.category for s in ALL_SKILLS.values()))


def get_available_skills(level: int, stats: dict[str, int]) -> list[Skill]:
    """Get skills that a player can use given their level and stats."""
    from pvp2.models import Stats
    player_stats = Stats(**{k: v for k, v in stats.items() if hasattr(Stats, k)})
    return [s for s in ALL_SKILLS.values() if s.meets_requirements(player_stats, level)]


def get_shop_page(page: int, per_page: int = 5) -> tuple[list[Skill], int]:
    """Get a page of skills for the shop. Returns (skills, total_pages)."""
    all_sorted = sorted(ALL_SKILLS.values(), key=lambda s: (s.min_level, s.price))
    total_pages = max(1, (len(all_sorted) + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    return all_sorted[start:end], total_pages
