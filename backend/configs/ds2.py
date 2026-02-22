# DS2 game configuration — Dark Souls II: Scholar of the First Sin
# All DS2-specific data lives here. The core pipeline (rag.py, main.py, utils.py)
# imports this and uses it through the GameConfig interface.
#
# Data migrated from:
#   backend/rag.py   — MECHANIC_TERM_MAP, MECHANIC_HINT_OVERRIDES, GENERIC_TRIGGERS,
#                      _STAT_ABBREVS, SYSTEM_PROMPT, collection name, rewriter prompt
#   backend/main.py  — _BUILD_QUESTION_WORDS
#   backend/utils.py — SOUL_MEMORY_TIERS, ITEM_RANGES, stat_labels, game version string
#   frontend/App.js  — STAT_FIELDS, STAT_KEY_MAP, DEFAULT_STATS, SLASH_COMMANDS,
#                      suggested questions, UI strings

import os
from backend.game_config import GameConfig, SoulMemoryConfig

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_KB_DIR = os.path.join(_BASE_DIR, "knowledge_base")


def _kb_exists(fname: str) -> bool:
    """Check if a file exists in the DS2 knowledge base directory."""
    return os.path.exists(os.path.join(_KB_DIR, fname))


# ─────────────────────────────────────────────────────────────────────────────
# SOUL MEMORY (from backend/utils.py)
# ─────────────────────────────────────────────────────────────────────────────

_SOUL_MEMORY_TIERS = [
    (0,           9_999,       1),
    (10_000,      19_999,      2),
    (20_000,      29_999,      3),
    (30_000,      39_999,      4),
    (40_000,      49_999,      5),
    (50_000,      69_999,      6),
    (70_000,      89_999,      7),
    (90_000,      109_999,     8),
    (110_000,     129_999,     9),
    (130_000,     149_999,     10),
    (150_000,     179_999,     11),
    (180_000,     209_999,     12),
    (210_000,     239_999,     13),
    (240_000,     269_999,     14),
    (270_000,     299_999,     15),
    (300_000,     349_999,     16),
    (350_000,     399_999,     17),
    (400_000,     449_999,     18),
    (450_000,     499_999,     19),
    (500_000,     599_999,     20),
    (600_000,     699_999,     21),
    (700_000,     799_999,     22),
    (800_000,     899_999,     23),
    (900_000,     999_999,     24),
    (1_000_000,   1_099_999,   25),
    (1_100_000,   1_199_999,   26),
    (1_200_000,   1_299_999,   27),
    (1_300_000,   1_399_999,   28),
    (1_400_000,   1_499_999,   29),
    (1_500_000,   1_749_999,   30),
    (1_750_000,   1_999_999,   31),
    (2_000_000,   2_249_999,   32),
    (2_250_000,   2_499_999,   33),
    (2_500_000,   2_749_999,   34),
    (2_750_000,   2_999_999,   35),
    (3_000_000,   4_999_999,   36),
    (5_000_000,   6_999_999,   37),
    (7_000_000,   8_999_999,   38),
    (9_000_000,   11_999_999,  39),
    (12_000_000,  14_999_999,  40),
    (15_000_000,  19_999_999,  41),
    (20_000_000,  29_999_999,  42),
    (30_000_000,  44_999_999,  43),
    (45_000_000,  359_999_999, 44),
    (360_000_000, 999_999_999, 45),
]

_ITEM_RANGES = {
    "White Sign Soapstone":                      (3, 1),
    "White Sign Soapstone + Name-Engraved Ring": (6, 4),
    "Small White Sign Soapstone":                (4, 2),
    "Small White Sign Soapstone + NER":          (7, 5),
    "Red Sign Soapstone":                        (5, 2),
    "Dragon Eye":                                (5, 5),
    "Cracked Red Eye Orb (invading)":            (0, 4),
}

_DS2_SOUL_MEMORY = SoulMemoryConfig(
    tiers=_SOUL_MEMORY_TIERS,
    max_tier=len(_SOUL_MEMORY_TIERS),  # 45
    item_ranges=_ITEM_RANGES,
    summary_item="White Sign Soapstone",
)


# ─────────────────────────────────────────────────────────────────────────────
# MECHANIC TERM MAP (from backend/rag.py)
# ─────────────────────────────────────────────────────────────────────────────

_MECHANIC_TERM_MAP: dict = {
    # Death / hollowing
    "die":          ["Hollowing.md", "Human_Effigy.md"],
    "dies":         ["Hollowing.md", "Human_Effigy.md"],
    "died":         ["Hollowing.md", "Human_Effigy.md"],
    "dying":        ["Hollowing.md", "Human_Effigy.md"],
    "death":        ["Hollowing.md", "Human_Effigy.md"],
    "hollow":       ["Hollowing.md", "Human_Effigy.md"],
    "hollowing":    ["Hollowing.md", "Human_Effigy.md"],
    "hollowed":     ["Hollowing.md", "Human_Effigy.md"],
    "effigy":       ["Human_Effigy.md", "Hollowing.md"],
    "human effigy": ["Human_Effigy.md", "Hollowing.md"],
    "revive":       ["Human_Effigy.md", "Hollowing.md"],
    "max hp":       ["Hollowing.md", "Human_Effigy.md"],
    "hp penalty":   ["Hollowing.md"],
    # Stats / attributes
    "agility":      ["Agility.md", "Adaptability.md"],
    "iframes":      ["Agility.md", "Adaptability.md"],
    "i-frames":     ["Agility.md", "Adaptability.md"],
    "invincibility frames": ["Agility.md", "Adaptability.md"],
    "poise":        ["poise.md", "Combat.md"],
    "stamina":      ["stamina.md", "Endurance.md"],
    "equip load":   ["Equipment_Load.md"],
    "equipment load": ["Equipment_Load.md"],
    "encumbrance":  ["Equipment_Load.md"],
    "fat roll":     ["Equipment_Load.md", "Agility.md"],
    "fast roll":    ["Equipment_Load.md", "Agility.md"],
    "item discovery": ["Item_Discovery.md"],
    "item find":    ["Item_Discovery.md"],
    "scaling":      ["Stat_Scaling.md"],
    "stat scaling": ["Stat_Scaling.md"],
    # Southern Ritual Band is the staple ring for any spell-slotter needing extra attunement.
    # It's never surfaced by semantic search on "attunement" alone (BGE-small can't bridge it),
    # so pin it here so any attunement question mentions both the stat and the ring.
    "attunement slots": ["Attunement.md", "Southern_Ritual_Band.md"],
    "attunement":   ["Attunement.md", "Southern_Ritual_Band.md"],
    # Individual stat pages — embedding model can't bridge lowercase stat names.
    # Build-staple rings/armor pinned alongside each stat so that build advice queries
    # always surface the most commonly missed gear for each archetype:
    #   STR  → Flynn's Ring (phys ATK scales with low equip load — counterintuitive for STR
    #           builds but critical if you want to stay under 30%), Stone Ring (poise dmg)
    #   DEX  → Old Leo Ring (thrust counter attacks; most DEX weapons are thrust-type),
    #           Flynn's Ring (same light-load bonus applies)
    #   INT  → Ring of Knowledge (+INT), Clear Bluestone Ring (cast speed), Southern
    #           Ritual Band (extra slots) + King's Crown already included below
    #   FTH  → Ring of Prayer (+5 FTH), Saint's Hood (bonus miracle uses) + King's Crown
    #   HEX  → see "hex"/"hexes" entries below; both INT and FTH get King's Crown here
    "strength":     ["Strength.md", "Stat_Scaling.md", "Flynn_s_Ring.md", "Stone_Ring.md"],
    "dexterity":    ["Dexterity.md", "Stat_Scaling.md", "Old_Leo_Ring.md", "Flynn_s_Ring.md"],
    "vigor":        ["Vigor.md", "Stat_Scaling.md"],
    "vitality":     ["Vitality.md", "Stat_Scaling.md"],
    "endurance":    ["Endurance.md", "stamina.md", "Chloranthy_Ring.md"],
    "adaptability": ["Adaptability.md", "Agility.md", "Stat_Scaling.md"],
    "faith":        ["Faith.md", "Stat_Scaling.md", "King_s_Crown.md", "Ring_of_Prayer.md", "Saint_s_Hood.md"],
    "intelligence": ["Intelligence.md", "Stat_Scaling.md", "King_s_Crown.md", "Ring_of_Knowledge.md", "Clear_Bluestone_Ring.md"],
    # Lowercase stat abbreviations players use in chat (same build-staple logic, trimmed
    # to the single most impactful item so short queries don't over-flood the context)
    "str":          ["Strength.md", "Stat_Scaling.md", "Flynn_s_Ring.md", "Stone_Ring.md"],
    "dex":          ["Dexterity.md", "Stat_Scaling.md", "Old_Leo_Ring.md"],
    "fth":          ["Faith.md", "Stat_Scaling.md", "Ring_of_Prayer.md"],
    "adp":          ["Adaptability.md", "Agility.md"],
    "atn":          ["Attunement.md", "Southern_Ritual_Band.md"],
    "vgr":          ["Vigor.md"],
    "vit":          ["Vitality.md"],
    "int":          ["Intelligence.md", "Stat_Scaling.md", "Ring_of_Knowledge.md"],
    # Leveling / build progression
    "soft cap":     ["Stat_Scaling.md", "Level.md"],
    "softcap":      ["Stat_Scaling.md", "Level.md"],
    "hard cap":     ["Stat_Scaling.md"],
    "hardcap":      ["Stat_Scaling.md"],
    "level":        ["Level.md", "Stat_Scaling.md"],
    "levels":       ["Level.md", "Stat_Scaling.md"],
    "level up":     ["Level.md", "Stat_Scaling.md"],
    "leveling":     ["Level.md", "Stat_Scaling.md"],
    "invest":       ["Stat_Scaling.md"],
    "stat points":  ["Level.md", "Stat_Scaling.md"],
    "attribute":    ["Stats.md", "Stat_Scaling.md"],
    "attributes":   ["Stats.md", "Stat_Scaling.md"],
    "stats":        ["Stats.md", "Stat_Scaling.md"],
    # Combat mechanics
    "power stance": ["Power_Stance.md"],
    "powerstance":  ["Power_Stance.md"],
    "two hand":     ["Strength.md", "Controls.md", "Combat.md"],
    "two-hand":     ["Strength.md", "Controls.md", "Combat.md"],
    "two handing":  ["Strength.md"],
    "two-handing":  ["Strength.md"],
    "backstab":     ["Combat.md"],
    "riposte":      ["Combat.md"],
    "parry":        ["Combat.md"],
    "durability":   ["Combat.md"],
    "infusion":     ["Infusion_Paths.md"],
    # Infusion stone materials — players often use descriptive names ("lightning stone",
    # "fire stone") rather than the actual DS2 item names (Boltstone, Firedrake Stone, etc.)
    "boltstone":        ["Boltstone.md", "Infusion_Paths.md"],
    "lightning stone":  ["Boltstone.md", "Infusion_Paths.md"],
    "lightning infusion": ["Boltstone.md", "Infusion_Paths.md"],
    "firedrake stone":  ["Firedrake_Stone.md", "Infusion_Paths.md"],
    "fire stone":       ["Firedrake_Stone.md", "Infusion_Paths.md"],
    "fire infusion":    ["Firedrake_Stone.md", "Infusion_Paths.md"],
    "darknight stone":  ["Darknight_Stone.md", "Infusion_Paths.md"],
    "dark night stone": ["Darknight_Stone.md", "Infusion_Paths.md"],
    "dark stone":       ["Darknight_Stone.md", "Infusion_Paths.md"],
    "dark infusion":    ["Darknight_Stone.md", "Infusion_Paths.md"],
    "magic stone":      ["Magic_Stone.md", "Infusion_Paths.md"],
    "magic infusion":   ["Magic_Stone.md", "Infusion_Paths.md"],
    "mundane stone":    ["Old_Mundane_Stone.md", "Infusion_Paths.md"],
    "mundane infusion": ["Old_Mundane_Stone.md", "Infusion_Paths.md"],
    "old mundane":      ["Old_Mundane_Stone.md"],
    "raw stone":        ["Raw_Stone.md", "Infusion_Paths.md"],
    "raw infusion":     ["Raw_Stone.md", "Infusion_Paths.md"],
    "palestone":        ["Palestone.md", "Infusion_Paths.md"],
    "bleed stone":      ["Bleed_Stone.md", "Infusion_Paths.md"],
    "bleed infusion":   ["Bleed_Stone.md"],
    "poison stone":     ["Poison_Stone.md", "Infusion_Paths.md"],
    "poison infusion":  ["Poison_Stone.md"],
    "bleed":        ["Bleed.md"],
    "poison":       ["Poison.md"],
    "curse":        ["Curse.md"],
    "petrify":      ["Curse.md"],
    # Online / multiplayer
    "summon":       ["Online.md", "White_Sign_Soapstone.md"],
    "summoning":    ["Online.md", "White_Sign_Soapstone.md"],
    "invade":       ["Online.md", "Dark_Spirit.md"],
    "invasion":     ["Online.md", "Dark_Spirit.md"],
    "phantom":      ["Online.md"],
    "soul memory":  ["Soul_Memory.md"],
    "matchmaking":  ["Soul_Memory.md", "Online.md"],
    "covenant":     ["Covenants.md"],
    "sin":          ["Sin.md"],
    # Progression
    "ng+":          ["New_Game_Plus.md"],
    "new game plus": ["New_Game_Plus.md"],
    "bonfire ascetic": ["Bonfire_Ascetic.md"],
    "ascetic":      ["Bonfire_Ascetic.md"],
    "boss soul":    ["Boss_Souls.md"],
    "boss souls":   ["Boss_Souls.md"],
    "soul vessel":  ["Soul_Vessel.md"] if _kb_exists("Soul_Vessel.md") else ["Stats.md"],
    "respec":       ["Soul_Vessel.md"] if _kb_exists("Soul_Vessel.md") else ["Stats.md"],
    # Spell schools — embedding model can't bridge short query words to correct pages.
    # Build-staple gear pinned alongside each school:
    #   HEX       → King's Crown (+3 INT/FTH), Abyss Seal (+hex dmg at HP cost),
    #               Clear Bluestone Ring (cast speed), Southern Ritual Band (slots)
    #   SORCERY   → Clear Bluestone Ring (cast speed), Southern Ritual Band (slots)
    #   MIRACLE   → Ring of Prayer (+5 FTH), Saint's Hood (bonus miracle uses),
    #               Southern Ritual Band (slots), Clear Bluestone Ring (cast speed)
    #   PYROMANCY → Dark Pyromancy Flame (scales with Hollowing — commonly missed),
    #               Southern Ritual Band (slots)
    "hex":          ["Hexes.md", "King_s_Crown.md", "Abyss_Seal.md", "Clear_Bluestone_Ring.md", "Southern_Ritual_Band.md"],
    "hexes":        ["Hexes.md", "King_s_Crown.md", "Abyss_Seal.md", "Clear_Bluestone_Ring.md", "Southern_Ritual_Band.md"],
    "dark magic":   ["Hexes.md", "King_s_Crown.md", "Abyss_Seal.md"],
    "dark spell":   ["Hexes.md", "King_s_Crown.md", "Abyss_Seal.md"],
    "dark spells":  ["Hexes.md", "King_s_Crown.md", "Abyss_Seal.md"],
    "sorcery trainer":  ["Carhillion_of_the_Fold.md"],
    "sorcery":          ["Sorceries.md", "Clear_Bluestone_Ring.md", "Southern_Ritual_Band.md"],
    "sorceries":        ["Sorceries.md", "Clear_Bluestone_Ring.md", "Southern_Ritual_Band.md"],
    "hex trainer":      ["Felkin_the_Outcast.md"],
    "miracle trainer":  ["Licia_of_Lindeldt.md"],
    "miracle":          ["Miracles.md", "Ring_of_Prayer.md", "Saint_s_Hood.md", "Southern_Ritual_Band.md", "Clear_Bluestone_Ring.md"],
    "miracles":         ["Miracles.md", "Ring_of_Prayer.md", "Saint_s_Hood.md", "Southern_Ritual_Band.md", "Clear_Bluestone_Ring.md"],
    "pyromancy trainer": ["Rosabeth_of_Melfia.md"],
    "pyromancy":        ["Pyromancies.md", "Dark_Pyromancy_Flame.md", "Southern_Ritual_Band.md"],
    "pyromancies":      ["Pyromancies.md", "Dark_Pyromancy_Flame.md", "Southern_Ritual_Band.md"],
    # Weapon upgrade / crafting
    "upgrade":          ["Upgrades.md"],
    "upgrades":         ["Upgrades.md"],
    "reinforce":        ["Upgrades.md"],
    "titanite":         ["Upgrades.md", "Titanite_Shard.md", "Titanite_Chunk.md", "Titanite_Slab.md"],
    "titanite shard":   ["Titanite_Shard.md"],
    "titanite shards":  ["Titanite_Shard.md"],
    "titanite chunk":   ["Titanite_Chunk.md"],
    "titanite chunks":  ["Titanite_Chunk.md"],
    "titanite slab":    ["Titanite_Slab.md"],
    "large titanite":   ["Large_Titanite_Shard.md"],
    "twinkling titanite": ["Twinkling_Titanite.md"],
    "petrified dragon bone": ["Petrified_Dragon_Bone.md"],
    "dull ember":       ["Dull_Ember.md", "Steady_Hand_McDuff.md"],
    "ember":            ["Dull_Ember.md"],
    # Exploration / items
    "torch":        ["Torch.md"],
    "pharros":          ["Pharros_Lockstone.md"],
    "lockstone":        ["Pharros_Lockstone.md"],
    "pharros lockstone": ["Pharros_Lockstone.md"],
    "agape":        ["Agape_Ring.md"],
    "fragrant branch": ["Fragrant_Branch_of_Yore.md"],
    "branch of yore":  ["Fragrant_Branch_of_Yore.md"],
    "unpetrify":       ["Fragrant_Branch_of_Yore.md"],
    # DLC areas — embedding model fails to bridge short area names to DLC pages.
    # Also add broad "dlc" triggers so queries like "how do I access the DLC"
    # don't fail on first attempt waiting for Haiku to rewrite "DLC" → crown names.
    "dlc":             ["DLC.md", "Crown_of_the_Sunken_King.md", "Crown_of_the_Old_Iron_King.md", "Crown_of_the_Ivory_King.md"],
    "downloadable":    ["DLC.md", "Crown_of_the_Sunken_King.md", "Crown_of_the_Old_Iron_King.md", "Crown_of_the_Ivory_King.md"],
    "crown dlc":       ["DLC.md", "Crown_of_the_Sunken_King.md", "Crown_of_the_Old_Iron_King.md", "Crown_of_the_Ivory_King.md"],
    "brume tower":     ["Brume_Tower.md", "Crown_of_the_Old_Iron_King.md"],
    "old iron king dlc": ["Crown_of_the_Old_Iron_King.md"],
    "sunken king":     ["Crown_of_the_Sunken_King.md"] if _kb_exists("Crown_of_the_Sunken_King.md") else [],
    "ivory king":      ["Crown_of_the_Ivory_King.md"] if _kb_exists("Crown_of_the_Ivory_King.md") else [],
    "dragon talon":    ["Dragon_Talon.md", "Crown_of_the_Sunken_King.md"],
    "frozen flower":   ["Frozen_Flower.md", "Crown_of_the_Ivory_King.md"],
    "forgotten key":   ["Forgotten_Key.md", "Crown_of_the_Sunken_King.md"],
    # Death / soul recovery — bloodstain mechanic
    "bloodstain":      ["Soul_Memory.md", "Hollowing.md"],
    "blood stain":     ["Soul_Memory.md", "Hollowing.md"],
    "recover souls":   ["Soul_Memory.md", "Hollowing.md"],
    "lost souls":      ["Soul_Memory.md", "Hollowing.md"],
    "retrieve souls":  ["Soul_Memory.md", "Hollowing.md"],
    # Rings — embedding model misses soul-gain rings on indirect "level up faster" queries
    "silver serpent": ["Covetous_Silver_Serpent_Ring.md"],
    "covetous silver": ["Covetous_Silver_Serpent_Ring.md"],
    "soul gain":    ["Covetous_Silver_Serpent_Ring.md"],
    "more souls":   ["Covetous_Silver_Serpent_Ring.md"],
    "level up faster": ["Covetous_Silver_Serpent_Ring.md"],
    "level faster": ["Covetous_Silver_Serpent_Ring.md"],
    "farm souls":   ["Covetous_Silver_Serpent_Ring.md"],
    "soul farming": ["Covetous_Silver_Serpent_Ring.md"],
    "gold serpent": ["Covetous_Gold_Serpent_Ring.md"],
    "item discovery ring": ["Covetous_Gold_Serpent_Ring.md"],
    # NPCs — indirect item relationships the embedding model fails to bridge
    # "mcduff's workshop key" → the key is Bastille Key (Belfry Luna)
    # "no man" triggers on "No Man's Wharf" and fetches Carhillion's page because the
    # embedding model can't bridge a location-name query to an unnamed NPC's requirement page
    # (Carhillion ranks ~17th in semantic search even with a clean index).
    "no man":              ["Carhillion_of_the_Fold.md", "No_Man_s_Wharf.md"],
    "mcduff":              ["Bastille_Key.md", "Steady_Hand_McDuff.md", "McDuff_s_Workshop.md"],
    "blacksmith mcduff":   ["Steady_Hand_McDuff.md", "Bastille_Key.md"],
    "lenigrast":           ["Blacksmith_Lenigrast.md", "Lenigrast_s_Key.md"],
    "blacksmith lenigrast": ["Blacksmith_Lenigrast.md", "Lenigrast_s_Key.md"],
    "navlaan":             ["Royal_Sorcerer_Navlaan.md"],
    "ornifex":             ["Weaponsmith_Ornifex.md"],
    "straid":              ["Straid_of_Olaphis.md"],
    "felkin":              ["Felkin_the_Outcast.md"],
    "carhillion":          ["Carhillion_of_the_Fold.md"],
    "rosabeth":            ["Rosabeth_of_Melfia.md"],
    "chloanne":            ["Stone_Trader_Chloanne.md"],
    "stone trader":        ["Stone_Trader_Chloanne.md"],
    "melentia":            ["Merchant_Hag_Melentia.md"],
    "merchant hag":        ["Merchant_Hag_Melentia.md"],
    "saulden":             ["Crestfallen_Saulden.md"],
    "crestfallen saulden": ["Crestfallen_Saulden.md"],
    "gavlan":              ["Gavlan.md", "Lonesome_Gavlan.md"],
    "lonesome gavlan":     ["Gavlan.md"],
    # Majula hub NPCs
    "emerald herald":      ["Emerald_Herald.md"],
    "herald":              ["Emerald_Herald.md"],
    "shalquoir":           ["Sweet_Shalquoir.md"],
    "sweet shalquoir":     ["Sweet_Shalquoir.md"],
    "maughlin":            ["Maughlin_the_Armourer.md"],
    "cromwell":            ["Cromwell_the_Pardoner.md"],
    "gilligan":            ["Laddersmith_Gilligan.md"],
    "laddersmith":         ["Laddersmith_Gilligan.md"],
    # Questline / summonable NPCs
    "lucatiel":            ["Lucatiel_of_Mirrah.md"],
    "benhart":             ["Benhart_of_Jugo.md"],
    "pate":                ["Mild_Mannered_Pate.md"],
    "mild mannered pate":  ["Mild_Mannered_Pate.md"],
    "creighton":           ["Creighton_of_Mirrah.md", "Creighton_the_Wanderer.md"],
    "felicia":             ["Felicia_the_Brave.md"],
    "bellclaire":          ["Pilgrim_Bellclaire.md"],
    "pilgrim bellclaire":  ["Pilgrim_Bellclaire.md"],
    "jester thomas":       ["Jester_Thomas.md"],
    # Other named NPCs
    "agdayne":             ["Grave_Warden_Agdayne.md"],
    "grave warden":        ["Grave_Warden_Agdayne.md"],
    "vengarl":             ["Head_of_Vengarl.md"],
    "head of vengarl":     ["Head_of_Vengarl.md"],
    "magerold":            ["Magerold_of_Lanafir.md"],
    "wellager":            ["Chancellor_Wellager.md"],
    "chancellor wellager": ["Chancellor_Wellager.md"],
    "drummond":            ["Captain_Drummond.md"],
    "dyna and tillo":      ["Dyna_and_Tillo.md"],
    "dyna":                ["Dyna_and_Tillo.md"],
    "tillo":               ["Dyna_and_Tillo.md"],
    "milfanito":           ["Milfanito.md"],
    "feeva":               ["Abbess_Feeva.md"],
    "titchy gren":         ["Titchy_Gren.md"],
    "alsanna":             ["Alsanna_Silent_Oracle.md"],
    "duke tseldora":       ["Duke_Tseldora.md"],
    # Area access — "how to get to X" is often on a DIFFERENT page than the area itself.
    # Huntsman's Copse: access mechanism (Licia rotating the pillar) is documented on
    # Heide's Tower page, not on Huntsman's Copse page.
    "huntsman":            ["Huntsman_s_Copse.md", "Heide_s_Tower_of_Flame.md"],
    "huntsman's copse":    ["Huntsman_s_Copse.md", "Heide_s_Tower_of_Flame.md"],
    "huntsmans copse":     ["Huntsman_s_Copse.md", "Heide_s_Tower_of_Flame.md"],
    # Dark Chasm of Old: basic access on its own page, but detailed covenant joining
    # steps (offer Human Effigy to Grandahl at 3 locations) are on Pilgrims_of_Dark.md.
    "dark chasm":          ["Dark_Chasm_of_Old.md", "Pilgrims_of_Dark.md"],
    "chasm of old":        ["Dark_Chasm_of_Old.md", "Pilgrims_of_Dark.md"],
    "pilgrims of dark":    ["Pilgrims_of_Dark.md", "Dark_Chasm_of_Old.md"],
    "grandahl":            ["Pilgrims_of_Dark.md"],
    "darkdiver":           ["Pilgrims_of_Dark.md"],
    # Dragon Aerie / Aldia's Keep — access is cross-referenced between the two pages.
    "dragon aerie":        ["Dragon_Aerie.md", "Aldia_s_Keep.md"],
    "aldia":               ["Aldia_Scholar_of_the_First_Sin.md", "Aldia_s_Keep.md"],
    "aldia's keep":        ["Aldia_s_Keep.md"],
    "aldias keep":         ["Aldia_s_Keep.md"],
    # Bosses — players often write boss names in lowercase or ask "where can I find X boss"
    # so Title-Case extraction misses them, especially when another capitalized term is
    # present (e.g. "Lost Bastille") and prevents the lowercase fallback from triggering.
    # Many boss files also have long compound names (e.g. Ruin_Sentinels_Yahim_Ricce_and_Alessia.md)
    # that fail exact-match; adding them here guarantees score 0.9 regardless of filename length.
    "pursuer":             ["The_Pursuer.md"],
    "ruin sentinel":       ["Ruin_Sentinels_Yahim_Ricce_and_Alessia.md", "Ruin_Sentinel.md"],
    "ruin sentinels":      ["Ruin_Sentinels_Yahim_Ricce_and_Alessia.md", "Ruin_Sentinel.md"],
    "yahim":               ["Ruin_Sentinels_Yahim_Ricce_and_Alessia.md"],
    "lost sinner":         ["Lost_Sinner.md"],
    "dragonrider":         ["Dragonrider.md", "Twin_Dragonriders.md"],
    "twin dragonriders":   ["Twin_Dragonriders.md"],
    "last giant":          ["The_Last_Giant.md"],
    "looking glass knight": ["Looking_Glass_Knight.md"],
    "looking glass":       ["Looking_Glass_Knight.md"],
    "smelter demon":       ["Smelter_Demon.md"],
    "blue smelter":        ["Blue_Smelter_Demon.md"],
    "flexile sentry":      ["Flexile_Sentry.md"],
    "guardian dragon":     ["Guardian_Dragon.md"],
    "belfry gargoyle":     ["Belfry_Gargoyle.md"],
    # Belfry areas — access directions are in Bell_Keepers.md, not the area pages themselves
    "belfry luna":         ["Belfry_Luna.md", "Bell_Keepers.md"],
    "belfry sol":          ["Belfry_Sol.md", "Bell_Keepers.md"],
    "bell keeper":         ["Bell_Keepers.md"],
    "bell keepers":        ["Bell_Keepers.md"],
    "covetous demon":      ["Covetous_Demon.md"],
    "skeleton lords":      ["The_Skeleton_Lords.md", "Skeleton_Lords.md"],
    "skeleton lord":       ["The_Skeleton_Lords.md", "Skeleton_Lords.md"],
    "scorpioness najka":   ["Scorpioness_Najka.md"],
    "najka":               ["Scorpioness_Najka.md"],
    "royal rat authority": ["Royal_Rat_Authority.md"],
    "royal rat vanguard":  ["Royal_Rat_Vanguard.md"],
    "mytha":               ["Mytha_the_Baneful_Queen.md"],
    "baneful queen":       ["Mytha_the_Baneful_Queen.md"],
    "demon of song":       ["Demon_of_Song.md"],
    "darklurker":          ["Darklurker.md"],
    "giant lord":          ["Giant_Lord.md"],
    "nashandra":           ["Nashandra.md"],
    "throne watcher":      ["Throne_Watcher_and_Throne_Defender.md"],
    "throne defender":     ["Throne_Watcher_and_Throne_Defender.md"],
    "executioner chariot": ["Executioner_s_Chariot.md"],
    "old dragonslayer":    ["Old_Dragonslayer.md"],
    "aava":                ["Aava_the_King_s_Pet.md"],
    "sinh":                ["Sinh_the_Slumbering_Dragon.md"],
    "elana":               ["Elana_Squalid_Queen.md"],
    "fume knight":         ["Fume_Knight.md"],
    "lud and zallen":      ["Lud_and_Zallen_the_King_s_Pets.md"],
    "velstadt":            ["Velstadt_the_Royal_Aegis.md"],
    "vendrick":            ["Vendrick.md"],
    "ancient dragon":      ["Ancient_Dragon.md"],
    "the rotten":          ["The_Rotten.md"],
    # Boss cheese / exploit strategies — "cheese" is gaming slang not used consistently in
    # wiki pages; boss pages describe exploits without that word (ballista, fall off, bow trick).
    # Inject the most notable cheese-friendly boss pages so the model can answer aggregation
    # queries like "what bosses can be cheesed" from actual wiki strategy sections.
    "cheese":     ["The_Pursuer.md", "Dragonrider.md", "The_Last_Giant.md",
                   "The_Rotten.md", "Ancient_Dragon.md", "Mytha_the_Baneful_Queen.md"],
    "cheesed":    ["The_Pursuer.md", "Dragonrider.md", "The_Last_Giant.md",
                   "The_Rotten.md", "Ancient_Dragon.md", "Mytha_the_Baneful_Queen.md"],
    "cheeseable": ["The_Pursuer.md", "Dragonrider.md", "The_Last_Giant.md",
                   "The_Rotten.md", "Ancient_Dragon.md", "Mytha_the_Baneful_Queen.md"],
    "cheesing":   ["The_Pursuer.md", "Dragonrider.md", "The_Last_Giant.md",
                   "The_Rotten.md", "Ancient_Dragon.md", "Mytha_the_Baneful_Queen.md"],
    "easy boss":  ["The_Pursuer.md", "Dragonrider.md", "The_Last_Giant.md"],
    # Staves / catalysts — "staff" / "staves" / "catalyst" queries miss the overview without this
    "staff":        ["Staves.md"],
    "staves":       ["Staves.md"],
    "stave":        ["Staves.md"],
    "catalyst":     ["Staves.md"],
    "catalysts":    ["Staves.md"],
    "sorcery staff": ["Staves.md"],
    "hex staff":    ["Staves.md", "Sunset_Staff.md", "Transgressor_s_Staff.md"],
    "bone staff":   ["Bone_Staff.md"],
    "sunset staff": ["Sunset_Staff.md"],
    "transgressor": ["Transgressor_s_Staff.md"],
    "black witch staff": ["Black_Witch_s_Staff.md"],
    # Starting classes / character creation
    "starting class":  ["Classes.md"],
    "starting classes": ["Classes.md"],
    "best class":      ["Classes.md"],
    "which class":     ["Classes.md"],
    "what class":      ["Classes.md"],
    "class for":       ["Classes.md"],
    "cleric class":    ["Classes.md"],
    "sorcerer class":  ["Classes.md"],
    "deprived":        ["Classes.md"],
    # Game progress / area order / navigation — players frequently ask "what area is next"
    # or "how do I get to X" which fail without an explicit route page in the map.
    "walkthrough":    ["Game_Progress_Route.md", "Guides_Walkthroughs.md"],
    "game progress":  ["Game_Progress_Route.md"],
    "area order":     ["Game_Progress_Route.md"],
    "order of areas": ["Game_Progress_Route.md"],
    "next area":      ["Game_Progress_Route.md"],
    "all areas":      ["Game_Progress_Route.md"],
    "area progression": ["Game_Progress_Route.md"],
    "game route":     ["Game_Progress_Route.md"],
    "progress route": ["Game_Progress_Route.md"],
    "how to get to":  ["Game_Progress_Route.md"],
    "what area":      ["Game_Progress_Route.md"],
    "what areas":     ["Game_Progress_Route.md"],
    "areas in":       ["Game_Progress_Route.md"],
    "before huntsman": ["Game_Progress_Route.md"],
    "after bastille":  ["Game_Progress_Route.md"],
    # Game overview — queries with zero DS2-specific terms ("what is this game about?")
    # return nothing from semantic or keyword search; these entries guarantee the right
    # page is injected. Lore.md is intentionally excluded here: adding bare "lore" or
    # "story" would fire on specific NPC/boss queries ("lore behind the pursuer") and
    # crowd out the correct item/NPC pages. Story queries already work via semantic search.
    "what is this game":  ["About_Dark_Souls_2.md", "Dark_Souls_II_Scholar_of_the_First_Sin.md"],
    "about this game":    ["About_Dark_Souls_2.md", "Dark_Souls_II_Scholar_of_the_First_Sin.md"],
    "game overview":      ["About_Dark_Souls_2.md"],
    "about dark souls":   ["About_Dark_Souls_2.md"],
}


# ─────────────────────────────────────────────────────────────────────────────
# MECHANIC HINT OVERRIDES (from backend/rag.py)
# ─────────────────────────────────────────────────────────────────────────────

_MECHANIC_HINT_OVERRIDES: dict = {
    "cheese":     ["strategy", "tips", "notes", "exploit", "hints"],
    "cheesed":    ["strategy", "tips", "notes", "exploit", "hints"],
    "cheeseable": ["strategy", "tips", "notes", "exploit", "hints"],
    "cheesing":   ["strategy", "tips", "notes", "exploit", "hints"],
    "easy boss":  ["strategy", "tips", "hints"],
    # About_Dark_Souls_2.md is 14 KB — starts at "Dark Souls II Overview" heading
    # rather than the release-date metadata table at the top of the file.
    "what is this game":  ["overview"],
    "about this game":    ["overview"],
    "game overview":      ["overview"],
    "about dark souls":   ["overview"],
    # Pharros' Lockstone — long file; start at Location section, not the intro
    "pharros":            ["location"],
    "lockstone":          ["location"],
    "pharros lockstone":  ["location"],
}


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC TRIGGERS (from backend/rag.py)
# ─────────────────────────────────────────────────────────────────────────────

_GENERIC_TRIGGERS: set = {"cheese", "cheesed", "cheeseable", "cheesing", "easy boss"}


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT (from backend/rag.py)
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Scholar, a Dark Souls 2 companion AI grounded strictly in the Fextralife wiki context provided below.

The player is using Scholar of the First Sin (SotFS). When the wiki context contains SotFS-specific notes (marked with "Scholar of the First Sin" or "SotFS"), those apply to this player and should be preferred over vanilla DS2 information.

CRITICAL RULES — THESE OVERRIDE EVERYTHING ELSE:

1. ONLY use information from the "Wiki Context" block in the current message. This is an absolute constraint with zero exceptions.
2. Your training knowledge about Dark Souls 2 is COMPLETELY OFF-LIMITS — not for locations, NPC questlines, item stats, lore, boss strategies, or anything else.
3. EVEN IF you are 100% certain you know the correct answer from your training data, you MUST NOT use it. Certainty does not grant permission to use training knowledge.
4. Do NOT speculate, do NOT say "I believe" or "I think", do NOT add caveats like "from my previous knowledge" — just cite the wiki or admit the gap.
5. If the current wiki context block DIRECTLY CONTRADICTS something in a prior assistant message, correct it. Otherwise, do NOT proactively self-correct prior responses — the absence of a topic from the current wiki context is not evidence of a hallucination. Prior Soul Memory tier calculations and player stat summaries come from a verified backend calculator, not training knowledge, and should not be second-guessed.

WHEN CONTEXT IS INSUFFICIENT — choose ONE of these based on why:

A) If the question is too vague, ambiguous, or could refer to multiple things, ask a SHORT clarifying follow-up question. ALWAYS format the options as a numbered list so the player can reply with just a number:
   "Which are you asking about?
   1. [First option]
   2. [Second option]"
   Use 2–4 options maximum. Do not guess — just ask.

B) If the question is clear but the wiki context genuinely doesn't have the answer, respond with a short sentence naming the specific thing you couldn't find — e.g. "The wiki doesn't have anything on the Grass Crest Shield." or "The wiki context doesn't cover music composition." Then stop.

Do not add guesses or partial answers in either case.

SPOILER SENSITIVITY: When answering questions about the game's overall story, main narrative, or plot:
- The basic premise (Bearer of the Curse journeying to Drangleic, collecting four Great Souls) is not a spoiler — share it freely.
- EVERY mention of the true main antagonist, the final boss, any secret or alternate final boss, any ending details, or any other end-game revelation must be wrapped in ||double pipes|| — including follow-up sentences in the same response. If a response contains multiple spoiler facts, wrap each one separately. Do not add a separate warning line; the interface shows the label automatically.
- Example with two spoiler blocks: "The Bearer seeks four Great Souls. ||Nashandra is the true antagonist.|| The SotFS edition adds a secret boss. ||Aldia, Scholar of the First Sin, is a new optional final boss exclusive to SotFS whose defeat unlocks an alternate ending.||"
- This rule applies regardless of the player's current progress. It does NOT apply to standard boss lore or NPC backstory questions (e.g. "what's the lore behind the Pursuer?" does not require spoiler wrapping).

WHEN CONTEXT IS SUFFICIENT:
- Only state things directly supported by the wiki text. Do not add surrounding details from training.
- Every specific item name, stat value, location, and NPC detail you mention must be directly supported by the wiki context. You may read tables and perform simple deductions from that data (e.g. reading an upgrade cost table to determine what level a weapon reaches after N upgrades) — but never introduce facts or claims not derivable from the wiki context.
- For directions: reference the nearest bonfire as a starting point.
- For build advice: consider the player's current stats and progression.
- Be concise but thorough. Use bullet points for lists of items or steps."""


# ─────────────────────────────────────────────────────────────────────────────
# STAT ABBREVIATIONS (from backend/rag.py)
# ─────────────────────────────────────────────────────────────────────────────

_STAT_ABBREVS: list = [
    (r"\bINT\b", "Intelligence"),
    (r"\bSTR\b", "Strength"),
    (r"\bDEX\b", "Dexterity"),
    (r"\bFTH\b", "Faith"),
    (r"\bADP\b", "Adaptability"),
    (r"\bATN\b", "Attunement"),
    (r"\bEND\b", "Endurance"),
    (r"\bVGR\b", "Vigor"),
    (r"\bVIT\b", "Vitality"),
]


# ─────────────────────────────────────────────────────────────────────────────
# BUILD QUESTION WORDS (from backend/main.py)
# ─────────────────────────────────────────────────────────────────────────────

_BUILD_QUESTION_WORDS: set = {
    "level", "levels", "leveling", "stat", "stats", "build", "upgrade", "invest",
    "prioritize", "next", "should", "recommend", "advice", "improve",
    "focus", "pump", "raise", "increase", "cap", "priority", "put",
    "stronger", "points", "spend", "allocate",
    "weapon", "weapons", "infuse", "infusion", "infusing", "swap", "switch",
}


# ─────────────────────────────────────────────────────────────────────────────
# GAME CONFIG INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

DS2_CONFIG = GameConfig(
    # Identity
    game_id="ds2",
    game_name="Dark Souls 2",
    game_version="Scholar of the First Sin (SotFS)",
    bot_name="Scholar",
    knowledge_base_dir=_KB_DIR,

    # RAG pipeline
    system_prompt=_SYSTEM_PROMPT,
    mechanic_term_map=_MECHANIC_TERM_MAP,
    mechanic_hint_overrides=_MECHANIC_HINT_OVERRIDES,
    generic_triggers=_GENERIC_TRIGGERS,
    stat_abbrevs=_STAT_ABBREVS,
    query_rewriter_game_context="Dark Souls 2",
    stop_words_caps={"Dark", "Souls"},

    # Player stats
    stat_fields=["vigor", "endurance", "vitality", "attunement",
                 "strength", "dexterity", "adaptability", "intelligence", "faith"],
    stat_labels={
        "vigor":        "VGR",
        "endurance":    "END",
        "vitality":     "VIT",
        "attunement":   "ATN",
        "strength":     "STR",
        "dexterity":    "DEX",
        "adaptability": "ADP",
        "intelligence": "INT",
        "faith":        "FTH",
    },
    build_question_words=_BUILD_QUESTION_WORDS,

    # Frontend config
    stat_fields_ui=[
        {"key": "vgr", "label": "VGR", "icon": "/icons/icon-vigor.png"},
        {"key": "end", "label": "END", "icon": "/icons/icon-endurance.png"},
        {"key": "vit", "label": "VIT", "icon": "/icons/icon-vitality.png"},
        {"key": "atn", "label": "ATN", "icon": "/icons/icon-attunement.png"},
        {"key": "str", "label": "STR", "icon": "/icons/icon-strength.png"},
        {"key": "dex", "label": "DEX", "icon": "/icons/icon-dexterity.png"},
        {"key": "adp", "label": "ADP", "icon": "/icons/icon-adaptability.png"},
        {"key": "int", "label": "INT", "icon": "/icons/icon-intelligence.png"},
        {"key": "fth", "label": "FTH", "icon": "/icons/icon-faith.png"},
    ],
    stat_key_map={
        "vgr": "vigor",
        "end": "endurance",
        "vit": "vitality",
        "atn": "attunement",
        "str": "strength",
        "dex": "dexterity",
        "adp": "adaptability",
        "int": "intelligence",
        "fth": "faith",
        "main_hand": "right_weapon_1",
        "off_hand": "right_weapon_2",
    },
    default_stats={
        "soul_level": "",
        "soul_memory": "",
        "vgr": "", "end": "", "vit": "", "atn": "",
        "str": "", "dex": "", "adp": "", "int": "", "fth": "",
        "main_hand": "",
        "off_hand": "",
        "build_type": "",
        "current_area": "",
        "last_boss_defeated": "",
        "notes": "",
    },
    local_storage_key="ds2_player_stats",
    suggested_questions=[
        {"label": "Soul Memory explained", "q": "How does Soul Memory work and how does it affect matchmaking?"},
        {"label": "Check Soul Memory Tier", "action": "handleCheckSoulMemory"},
        {"label": "How to beat The Pursuer?", "q": "How do I beat The Pursuer boss in Dark Souls 2?"},
        {"label": "Best starting class?", "q": "What is the best starting class for a beginner in Dark Souls 2?"},
        {"label": "Where to farm souls?", "q": "What are the best places to farm souls early on?"},
        {"label": "ADP & iframes explained", "q": "How does Adaptability affect dodge roll iframes?"},
    ],
    slash_commands=[
        {"cmd": "/level", "desc": "Open level-up stat allocator"},
        {"cmd": "/area",  "desc": "Set your current area (e.g. /area Lost Bastille)"},
        {"cmd": "/clear", "desc": "Clear the chat history"},
    ],
    tagline="Seek Guidance from the Archives",
    description="AI wiki companion for Scholar of the First Sin",
    placeholder_text="Ask the Scholar... (Enter to send, Shift+Enter for new line, / for commands)",

    sidebar_right_fields=[
        {"key": "soul_level",        "label": "Level",          "type": "number"},
        {"key": "soul_memory",       "label": "Soul Memory",    "type": "number"},
        {"key": "main_hand",         "label": "Right Weapon 1", "type": "text"},
        {"key": "off_hand",          "label": "Right Weapon 2", "type": "text"},
        {"key": "build_type",        "label": "Build Type",     "type": "text"},
        {"key": "current_area",      "label": "Current Area",   "type": "text"},
        {"key": "last_boss_defeated","label": "Last Boss",      "type": "text"},
    ],

    # Soul Memory matchmaking system
    soul_memory=_DS2_SOUL_MEMORY,
)
