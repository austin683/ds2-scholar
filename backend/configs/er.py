# Elden Ring game configuration
# All Elden Ring-specific data lives here. The core pipeline (rag.py, main.py, utils.py)
# imports this and uses it through the GameConfig interface.
#
# To activate: set GAME_ID=er in the environment before starting the backend.

import os
from backend.game_config import GameConfig

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_KB_DIR = os.path.join(_BASE_DIR, "knowledge_base_er")


# ─────────────────────────────────────────────────────────────────────────────
# MECHANIC TERM MAP
# Lowercase trigger → [wiki filenames]. Bridges the embedding gap for terms
# that BGE-small can't reliably map to the correct pages.
# ─────────────────────────────────────────────────────────────────────────────

_MECHANIC_TERM_MAP: dict = {
    # ── Death / death mechanics ───────────────────────────────────────────────
    "die":              ["Runes.md"],
    "dies":             ["Runes.md"],
    "died":             ["Runes.md"],
    "dying":            ["Runes.md"],
    "death":            ["Runes.md"],
    "lose runes":       ["Runes.md"],
    "lost runes":       ["Runes.md"],
    "recover runes":    ["Runes.md"],

    # ── Stats / attributes ────────────────────────────────────────────────────
    "iframes":              ["Equip_Load.md", "Stats.md"],
    "i-frames":             ["Equip_Load.md", "Stats.md"],
    "invincibility frames": ["Equip_Load.md"],
    "poise":                ["Poise.md"],
    "stamina":              ["Stamina.md", "Endurance.md"],
    "equip load":           ["Equip_Load.md"],
    "equipment load":       ["Equip_Load.md"],
    "encumbrance":          ["Equip_Load.md"],
    "fat roll":             ["Equip_Load.md"],
    "fast roll":            ["Equip_Load.md"],
    "item discovery":       ["Stats.md"],
    "item find":            ["Stats.md"],
    "scaling":              ["Stats.md", "Level.md"],
    "stat scaling":         ["Stats.md"],
    "fp":                   ["FP.md", "Mind.md"],
    "focus points":         ["FP.md", "Mind.md"],
    "mana":                 ["FP.md", "Mind.md"],
    "stance break":         ["Poise.md"],
    "posture break":        ["Poise.md"],
    "guard counter":        ["Poise.md"],
    # Stats with build-staple talismans pinned
    "vigor":            ["Vigor.md", "Stats.md"],
    "mind":             ["Mind.md", "FP.md", "Stats.md"],
    "endurance":        ["Endurance.md", "Stamina.md", "Equip_Load.md"],
    "strength":         ["Strength.md", "Stats.md"],
    "dexterity":        ["Dexterity.md", "Stats.md"],
    "intelligence":     ["Intelligence.md", "Stats.md", "Radagon_Icon.md"],
    "faith":            ["Faith.md", "Stats.md"],
    "arcane":           ["Arcane.md", "Stats.md"],
    # Abbreviated stat names
    "vig":  ["Vigor.md"],
    "mnd":  ["Mind.md", "FP.md"],
    "end":  ["Endurance.md", "Stamina.md"],
    "str":  ["Strength.md", "Stats.md"],
    "dex":  ["Dexterity.md", "Stats.md"],
    "int":  ["Intelligence.md", "Stats.md"],
    "fai":  ["Faith.md", "Stats.md"],
    "arc":  ["Arcane.md", "Stats.md"],

    # ── Leveling / build progression ──────────────────────────────────────────
    "soft cap":     ["Stats.md", "Level.md"],
    "softcap":      ["Stats.md", "Level.md"],
    "hard cap":     ["Stats.md"],
    "hardcap":      ["Stats.md"],
    "level":        ["Level.md", "Stats.md"],
    "levels":       ["Level.md", "Stats.md"],
    "level up":     ["Level.md", "Stats.md"],
    "leveling":     ["Level.md", "Stats.md"],
    "invest":       ["Stats.md"],
    "stat points":  ["Level.md", "Stats.md"],
    "attribute":    ["Stats.md"],
    "attributes":   ["Stats.md"],
    "stats":        ["Stats.md"],
    # ── Recommended level by location ─────────────────────────────────────────
    "recommended level":        ["Recommended_Level_by_Location.md"],
    "level recommendation":     ["Recommended_Level_by_Location.md"],
    "level range":              ["Recommended_Level_by_Location.md"],
    "what level":               ["Recommended_Level_by_Location.md", "Level.md"],
    "am i overleveled":         ["Recommended_Level_by_Location.md"],
    "am i underleveled":        ["Recommended_Level_by_Location.md"],
    "good level":               ["Recommended_Level_by_Location.md"],
    "right level":              ["Recommended_Level_by_Location.md"],
    "too low level":            ["Recommended_Level_by_Location.md"],
    "too high level":           ["Recommended_Level_by_Location.md"],
    "level for":                ["Recommended_Level_by_Location.md"],
    "level for this area":      ["Recommended_Level_by_Location.md"],
    "level for this boss":      ["Recommended_Level_by_Location.md"],
    "under leveled":            ["Recommended_Level_by_Location.md"],
    "over leveled":             ["Recommended_Level_by_Location.md"],
    "underleveled":             ["Recommended_Level_by_Location.md"],
    "overleveled":              ["Recommended_Level_by_Location.md"],

    # ── Classes / starting stats ──────────────────────────────────────────────
    "class":            ["Classes.md"],
    "classes":          ["Classes.md"],
    "starting class":   ["Classes.md"],
    "starting classes": ["Classes.md"],
    "starting stats":   ["Classes.md"],
    "starting stat":    ["Classes.md"],
    "base stats":       ["Classes.md"],
    "which class":      ["Classes.md"],
    "best class":       ["Classes.md"],
    # Individual class names → their dedicated page + Classes.md for comparison.
    # "hero", "warrior", "bandit" omitted — too generic (boss names, enemy types).
    "vagabond":     ["Vagabond.md",     "Classes.md"],
    "astrologer":   ["Astrologer.md",   "Classes.md"],
    "prisoner":     ["Prisoner.md",     "Classes.md"],
    "confessor":    ["Confessor.md",    "Classes.md"],
    "wretch":       ["Wretch.md",       "Classes.md"],
    "prophet":      ["Prophet.md",      "Classes.md"],
    "samurai":      ["Samurai.md",      "Classes.md"],

    # ── Status effects ────────────────────────────────────────────────────────
    "bleed":        ["Hemorrhage.md"],
    "blood loss":   ["Hemorrhage.md"],
    "hemorrhage":   ["Hemorrhage.md"],
    "scarlet rot":  ["Scarlet_Rot.md"],
    "rot":          ["Scarlet_Rot.md"],
    "frostbite":    ["Frostbite.md"],
    "frost":        ["Frostbite.md"],
    "poison":       ["Poison.md"],
    "madness":      ["Madness.md"],
    "sleep":        ["Sleep.md"],
    "death blight": ["Death_Blight.md"],
    "blight":       ["Death_Blight.md"],
    "status effect":["Stats.md"],

    # ── Upgrade system ────────────────────────────────────────────────────────
    "smithing stone":       ["Smithing_Stone.md"],
    "smithing stones":      ["Smithing_Stone.md"],
    "somber smithing stone":["Somber_Smithing_Stone.md"],
    "somber stone":         ["Somber_Smithing_Stone.md"],
    "upgrade":              ["Smithing_Stone.md", "Whetstone_Knife.md"],
    "upgrade weapon":       ["Smithing_Stone.md"],
    "whetstone":            ["Whetstone_Knife.md"],
    "whetblade":            ["Whetblades.md"],
    "+25":                  ["Smithing_Stone.md"],
    "+10":                  ["Somber_Smithing_Stone.md"],

    # ── Magic / Spells ────────────────────────────────────────────────────────
    "incantation":      ["Incantations.md"],
    "incantations":     ["Incantations.md"],
    "incant scaling":   ["Incant_Scaling.md"],
    "sorcery":          ["Sorceries.md"],
    "sorceries":        ["Sorceries.md"],
    "spell":            ["Incantations.md", "Sorceries.md"],
    "spells":           ["Incantations.md", "Sorceries.md"],
    "sacred seal":      ["Sacred_Seals.md"],
    "sacred seals":     ["Sacred_Seals.md"],
    "memory slot":      ["Memory_Slots.md", "Memory_Stone.md"],
    "memory slots":     ["Memory_Slots.md", "Memory_Stone.md"],
    "spell slot":       ["Memory_Slots.md", "Memory_Stone.md"],
    "spell slots":      ["Memory_Slots.md", "Memory_Stone.md"],
    "memory stone":     ["Memory_Stone.md", "Memory_Slots.md"],
    "memory stones":    ["Memory_Stones.md", "Memory_Slots.md"],
    "memorize":         ["Memory_Slots.md"],

    # ── Armor / fashion ───────────────────────────────────────────────────────
    "armor":        ["Armor.md", "Armor_Set.md"],
    "armour":       ["Armor.md", "Armor_Set.md"],
    "armor set":    ["Armor_Set.md", "Armor.md"],
    "armor sets":   ["Armor_Set.md", "Armor.md"],
    "outfit":       ["Armor.md", "Armor_Set.md"],
    "clothes":      ["Armor.md", "Armor_Set.md"],
    "fashion":      ["Armor.md", "Armor_Set.md"],
    "drip":         ["Armor.md", "Armor_Set.md"],
    "chest piece":  ["Armor.md"],
    "helm":         ["Armor.md"],
    "gauntlets":    ["Armor.md"],
    "greaves":      ["Armor.md"],

    # ── Weapon buffs / body buffs ─────────────────────────────────────────────
    "weapon buff":      ["Buffs_and_Debuffs.md", "Flame_Grant_Me_Strength.md", "Golden_Vow.md"],
    "buff weapon":      ["Buffs_and_Debuffs.md", "Flame_Grant_Me_Strength.md"],
    "buff incantation": ["Buffs_and_Debuffs.md", "Flame_Grant_Me_Strength.md", "Golden_Vow.md"],
    "attack buff":      ["Buffs_and_Debuffs.md", "Flame_Grant_Me_Strength.md", "Golden_Vow.md"],
    "damage buff":      ["Buffs_and_Debuffs.md", "Flame_Grant_Me_Strength.md"],
    "body buff":        ["Buffs_and_Debuffs.md", "Flame_Grant_Me_Strength.md"],
    "armament buff":    ["Buffs_and_Debuffs.md", "Order_s_Blade.md", "Bloodflame_Blade.md"],
    "physbuff":         ["Flame_Grant_Me_Strength.md"],
    "golden vow":       ["Golden_Vow.md", "Golden_Vow_Spell.md"],

    # ── Specific weapons ──────────────────────────────────────────────────────
    "winged scythe":    ["Winged_Scythe.md"],
    "whip":             ["Whip.md", "Whips.md"],
    "flail":            ["Flail.md"],
    "morning star":     ["Morning_Star.md"],
    "moonveil":         ["Moonveil.md"],
    "rivers of blood":  ["Rivers_of_Blood.md"],

    # ── Black Flame incantations ──────────────────────────────────────────────
    "black flame":              ["Black_Flame.md", "Incantations.md"],
    "black flame blade":        ["Black_Flame_Blade.md", "Buffs_and_Debuffs.md"],
    "black flame ritual":       ["Black_Flame_Ritual.md"],
    "black flame tornado":      ["Black_Flame_Tornado.md"],
    "black flame's protection": ["Black_Flame_s_Protection.md"],
    "scouring black flame":     ["Scouring_Black_Flame.md"],
    "godskin":                  ["Godskin_Prayerbook.md", "Black_Flame.md", "Black_Flame_Blade.md"],
    "godskin prayerbook":       ["Godskin_Prayerbook.md", "Black_Flame.md", "Black_Flame_Blade.md"],

    # ── Ashes of War ──────────────────────────────────────────────────────────
    "ash of war":   ["Ashes_of_War.md"],
    "ashes of war": ["Ashes_of_War.md"],
    "skill":        ["Ashes_of_War.md"],
    "weapon skill": ["Ashes_of_War.md"],
    "affinity":     ["Ashes_of_War.md", "Whetblades.md"],

    # ── Spirit Ashes ──────────────────────────────────────────────────────────
    "spirit ash":   ["Spirit_Ashes.md"],
    "spirit ashes": ["Spirit_Ashes.md"],
    "summon":       ["Spirit_Ashes.md", "Multiplayer_Items.md"],
    "spirit summon":["Spirit_Ashes.md"],
    "spectral steed whistle": ["Torrent.md"],

    # ── Flasks / consumables ──────────────────────────────────────────────────
    "lantern":          ["Lantern.md"],
    "hand lantern":     ["Lantern.md"],
    "flask":            ["Flask_of_Crimson_Tears.md", "Flask_of_Cerulean_Tears.md"],
    "crimson tear":     ["Flask_of_Crimson_Tears.md"],
    "cerulean tear":    ["Flask_of_Cerulean_Tears.md"],
    "wondrous physick": ["Flask_of_Wondrous_Physick.md"],
    "golden seed":      ["Golden_Seed.md"],
    "sacred tear":      ["Sacred_Tear.md"],
    "physick":          ["Flask_of_Wondrous_Physick.md"],

    # ── Runes / progression ───────────────────────────────────────────────────
    "rune":             ["Runes.md"],
    "runes":            ["Runes.md"],
    "rune arc":         ["Rune_Arc.md", "Great_Runes.md"],
    "great rune":       ["Great_Runes.md", "Rune_Arc.md"],
    "great runes":      ["Great_Runes.md"],
    "remembrance":      ["Remembrances.md"],
    "remembrances":     ["Remembrances.md"],

    # ── Multiplayer ───────────────────────────────────────────────────────────
    "co-op":                    ["Multiplayer_Coop_and_Online.md"],
    "coop":                     ["Multiplayer_Coop_and_Online.md"],
    "cooperate":                ["Multiplayer_Coop_and_Online.md"],
    "online":                   ["Multiplayer_Coop_and_Online.md"],
    "invasion":                 ["Multiplayer_Coop_and_Online.md", "Bloody_Finger.md"],
    "invade":                   ["Multiplayer_Coop_and_Online.md", "Bloody_Finger.md"],
    "multiplayer":              ["Multiplayer_Coop_and_Online.md", "Multiplayer_Items.md"],
    "pvp":                      ["Multiplayer_Coop_and_Online.md"],
    "furlcalling finger remedy":["Furlcalling_Finger_Remedy.md"],
    "bloody finger":            ["Bloody_Finger.md"],
    "blue cipher ring":         ["Blue_Cipher_Ring.md"],
    "white cipher ring":        ["White_Cipher_Ring.md"],

    # ── Mount ─────────────────────────────────────────────────────────────────
    "torrent":  ["Torrent.md"],
    "horse":    ["Torrent.md"],
    "mount":    ["Torrent.md"],

    # ── Sites of Grace ────────────────────────────────────────────────────────
    "grace":            ["Sites_of_Grace.md"],
    "site of grace":    ["Sites_of_Grace.md"],
    "sites of grace":   ["Sites_of_Grace.md"],
    "bonfire":          ["Sites_of_Grace.md"],  # common player shorthand
    "rest":             ["Sites_of_Grace.md"],

    # ── Key locations ─────────────────────────────────────────────────────────
    "dragon-burnt ruins":   ["Dragon-Burnt_Ruins.md"],
    "dragon burnt ruins":   ["Dragon-Burnt_Ruins.md"],
    "dragon-burnt":         ["Dragon-Burnt_Ruins.md"],
    "limgrave":             ["Limgrave.md"],
    "stormveil":            ["Stormveil_Castle.md"],
    "stormveil castle":     ["Stormveil_Castle.md"],
    "liurnia":              ["Liurnia_of_the_Lakes.md"],
    "raya lucaria":         ["Raya_Lucaria_Academy.md"],
    "academy":              ["Raya_Lucaria_Academy.md"],
    "caelid":               ["Caelid.md"],
    "altus plateau":        ["Altus_Plateau.md"],
    "altus":                ["Altus_Plateau.md"],
    "mountaintops":         ["Mountaintops_of_the_Giants.md"],
    "giants":               ["Mountaintops_of_the_Giants.md"],
    "consecrated snowfield":["Consecrated_Snowfield.md"],
    "snowfield":            ["Consecrated_Snowfield.md"],
    "leyndell":             ["Leyndell.md"],
    "capital":              ["Leyndell.md"],
    "farum azula":          ["Crumbling_Farum_Azula.md"],
    "crumbling farum":      ["Crumbling_Farum_Azula.md"],
    "mohgwyn":              ["Mohgwyn_Palace.md"],
    "mohgwyn palace":       ["Mohgwyn_Palace.md"],
    "siofra":               ["Siofra_River.md"],
    "ainsel":               ["Ainsel_River.md"],
    "nokron":               ["Nokron_Eternal_City.md"],
    "roundtable":           ["Roundtable_Hold.md"],
    "roundtable hold":      ["Roundtable_Hold.md"],
    "erdtree":              ["Erdtree.md"],

    # ── Key NPCs ──────────────────────────────────────────────────────────────
    "ranni":        ["Ranni_the_Witch.md"],
    "melina":       ["Melina.md"],
    "enia":         ["Enia.md"],
    "varre":        ["White_Mask_Varre.md"],
    "blaidd":       ["Blaidd.md"],
    "fia":          ["Fia.md"],
    "dung eater":   ["Dung_Eater.md"],
    "corhyn":       ["Brother_Corhyn.md"],
    "miriel":       ["Miriel_Pastor_of_Vows.md"],
    "goldmask":     ["Goldmask.md"],
    "nepheli":      ["Nepheli_Loux.md"],
    "diallos":      ["Diallos.md"],
    "hyetta":       ["Hyetta.md"],
    "alexander":    ["Iron_Fist_Alexander.md"],
    "iron fist":    ["Iron_Fist_Alexander.md"],
    "millicent":    ["Millicent.md"],
    "patches":      ["Patches.md"],
    "sellen":       ["Sorceress_Sellen.md"],
    "tanith":       ["Tanith.md"],

    # ── Key bosses ────────────────────────────────────────────────────────────
    "godrick":          ["Godrick_the_Grafted.md"],
    "rennala":          ["Rennala_Queen_of_the_Full_Moon.md"],
    "radahn":           ["Starscourge_Radahn.md"],
    "malenia":          ["Malenia_Blade_of_Miquella.md"],
    "maliketh":         ["Maliketh_the_Black_Blade.md"],
    "morgott":          ["Morgott_the_Omen_King.md"],
    "mohg":             ["Mohg_Lord_of_Blood.md"],
    "fire giant":       ["Fire_Giant.md"],
    "godfrey":          ["Godfrey_First_Elden_Lord.md"],
    "elden beast":      ["Elden_Beast.md"],
    "radagon":          ["Radagon_of_the_Golden_Order.md"],
    "valiant gargoyle": ["Valiant_Gargoyle.md"],
    "valiant gargoyles":["Valiant_Gargoyle.md"],

    # ── Character creation ────────────────────────────────────────────────────
    "keepsake":             ["Keepsakes.md"],
    "keepsakes":            ["Keepsakes.md"],
    "starting gift":        ["Keepsakes.md"],
    "starting keepsake":    ["Keepsakes.md"],
    "best keepsake":        ["Keepsakes.md"],

    # ── Game overview ─────────────────────────────────────────────────────────
    "what is this game":    ["Elden_Ring.md", "Game_Progress_Route.md"],
    "about this game":      ["Elden_Ring.md"],
    "game overview":        ["Elden_Ring.md"],
    "about elden ring":     ["Elden_Ring.md"],
    "progression":          ["Game_Progress_Route.md"],
    "where to go":          ["Game_Progress_Route.md"],
    "what order":           ["Game_Progress_Route.md"],
    "new game plus":        ["New_Game_Plus.md"],
    "ng+":                  ["New_Game_Plus.md"],
}


# ─────────────────────────────────────────────────────────────────────────────
# MECHANIC HINT OVERRIDES
# ─────────────────────────────────────────────────────────────────────────────

_MECHANIC_HINT_OVERRIDES: dict = {
    "cheese":       ["strategy", "tips", "notes", "exploit", "hints"],
    "cheesed":      ["strategy", "tips", "notes", "exploit", "hints"],
    "cheeseable":   ["strategy", "tips", "notes", "exploit", "hints"],
    "cheesing":     ["strategy", "tips", "notes", "exploit", "hints"],
    "easy boss":    ["strategy", "tips", "hints"],
    "what is this game":    ["overview"],
    "about this game":      ["overview"],
    "game overview":        ["overview"],
    "about elden ring":     ["overview"],
    # Dragon-Burnt Ruins: transport chest info is near end of file; start at Walkthrough heading
    "dragon-burnt ruins":   ["walkthrough", "chest", "transporter"],
    "dragon burnt ruins":   ["walkthrough", "chest", "transporter"],
    "dragon-burnt":         ["walkthrough", "chest", "transporter"],
}


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC TRIGGERS
# ─────────────────────────────────────────────────────────────────────────────

_GENERIC_TRIGGERS: set = {"cheese", "cheesed", "cheeseable", "cheesing", "easy boss"}


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Guide, an Elden Ring companion AI grounded strictly in the Fextralife wiki context provided below.

CRITICAL RULES — THESE OVERRIDE EVERYTHING ELSE:

1. ONLY use information from the "Wiki Context" block in the current message. This is an absolute constraint with zero exceptions.
2. Your training knowledge about Elden Ring is COMPLETELY OFF-LIMITS — not for locations, NPC questlines, item stats, lore, boss strategies, or anything else.
3. EVEN IF you are 100% certain you know the correct answer from your training data, you MUST NOT use it. Certainty does not grant permission to use training knowledge.
4. Do NOT speculate, do NOT say "I believe" or "I think", do NOT add caveats like "from my previous knowledge" — just cite the wiki or admit the gap. If referencing something covered in an earlier message in this conversation, say "from earlier in our conversation" — never "from prior context" or "from my training".
5. If the current wiki context block DIRECTLY CONTRADICTS something in a prior assistant message, correct it. Otherwise, do NOT proactively self-correct prior responses — the absence of a topic from the current wiki context is not evidence of a hallucination.

WHEN CONTEXT IS INSUFFICIENT — choose ONE of these based on why:

A) If the question is too vague, ambiguous, or could refer to multiple things, ask a SHORT clarifying follow-up question. ALWAYS format the options as a numbered list so the player can reply with just a number:
   "Which are you asking about?
   1. [First option]
   2. [Second option]"
   Use 2–4 options maximum. Do not guess — just ask.

B) If the question is clear but the wiki context genuinely doesn't have the answer, respond with a short sentence naming the specific thing you couldn't find — e.g. "The wiki doesn't have anything on the Grafted Blade Greatsword." or "The wiki context doesn't cover that mechanic." Then stop.

Do not add guesses or partial answers in either case.

SPOILER SENSITIVITY: The player may be at any point in the game. Protect them from anything they haven't seen yet. This rule applies at all times, even for questline tips and warnings.

Never needs spoiler tags:
- Basic premise (Tarnished seeks to mend the Elden Ring and become Elden Lord)
- That an NPC exists, where to find them, or what service they provide
- General mechanic explanations and stat info

Always wrap in ||double pipes||:
- Whether a questline leads to, unlocks, or affects a specific game ending — including statements like "her questline affects the endings" or "this leads to an alternate ending"
- NPC fates, deaths, or permanent disappearances the player hasn't described witnessing (e.g. "Seluvis will die", "she vanishes permanently")
- Any warning phrased as "before you defeat X" or "before X happens" where X is a late-game boss or world-state change the player hasn't mentioned (e.g. Maliketh, Godfrey, Radagon, the Elden Beast)
- Names of late-game areas the player hasn't mentioned visiting (e.g. Ashen Capital, Farum Azula, Mountaintops of the Giants, Mohgwyn Palace)
- Major world-state changes triggered by game progression (e.g. a city transforming, a location becoming inaccessible)
- Any revelation that a character is secretly someone or something else (e.g. identity reveals, true forms)

Wrapping rules:
- Tag only the spoiler sentence(s), not the surrounding safe context
- Use separate ||pipes|| for each distinct spoiler moment
- NEVER place ||pipes|| around an item inside a numbered or bulleted list — this breaks rendering. Pull the spoiler out as a separate paragraph before or after the list instead.
- Example: "Ranni's questline is expansive and has many steps. ||It is tied to one of the game's alternate endings.|| You'll need to speak with her at Ranni's Rise to begin."

WHEN CONTEXT IS SUFFICIENT:
- Only state things directly supported by the wiki text. Do not add surrounding details from training.
- Every specific item name, stat value, location, and NPC detail you mention must be directly supported by the wiki context. You may read tables and perform simple deductions from that data — but never introduce facts or claims not derivable from the wiki context.
- For directions: reference the nearest Site of Grace as a starting point.
- For build advice: consider the player's current stats and progression.
- Be concise but thorough. Use bullet points for lists of items or steps."""


# ─────────────────────────────────────────────────────────────────────────────
# STAT ABBREVIATIONS
# ─────────────────────────────────────────────────────────────────────────────

_STAT_ABBREVS: list = [
    (r"\bVIG\b", "Vigor"),
    (r"\bMND\b", "Mind"),
    (r"\bEND\b", "Endurance"),
    (r"\bSTR\b", "Strength"),
    (r"\bDEX\b", "Dexterity"),
    (r"\bINT\b", "Intelligence"),
    (r"\bFAI\b", "Faith"),
    (r"\bARC\b", "Arcane"),
]


# ─────────────────────────────────────────────────────────────────────────────
# BUILD QUESTION WORDS
# ─────────────────────────────────────────────────────────────────────────────

_BUILD_QUESTION_WORDS: set = {
    "level", "levels", "leveling", "stat", "stats", "build", "upgrade", "invest",
    "prioritize", "next", "should", "recommend", "advice", "improve",
    "focus", "pump", "raise", "increase", "cap", "priority", "put",
    "stronger", "points", "spend", "allocate",
    "weapon", "weapons", "infuse", "infusion", "infusing", "swap", "switch",
    "ash", "affinity",
}


# ─────────────────────────────────────────────────────────────────────────────
# GAME CONFIG INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

ER_CONFIG = GameConfig(
    # Identity
    game_id="er",
    game_name="Elden Ring",
    game_version="Elden Ring",
    bot_name="Guide",
    knowledge_base_dir=_KB_DIR,

    # RAG pipeline
    system_prompt=_SYSTEM_PROMPT,
    mechanic_term_map=_MECHANIC_TERM_MAP,
    mechanic_hint_overrides=_MECHANIC_HINT_OVERRIDES,
    generic_triggers=_GENERIC_TRIGGERS,
    stat_abbrevs=_STAT_ABBREVS,
    query_rewriter_game_context="Elden Ring",
    stop_words_caps={"Elden", "Ring"},

    # Player stats
    stat_fields=["vigor", "mind", "endurance", "strength", "dexterity",
                 "intelligence", "faith", "arcane"],
    stat_labels={
        "vigor":        "VIG",
        "mind":         "MND",
        "endurance":    "END",
        "strength":     "STR",
        "dexterity":    "DEX",
        "intelligence": "INT",
        "faith":        "FAI",
        "arcane":       "ARC",
    },
    build_question_words=_BUILD_QUESTION_WORDS,

    # Frontend config
    stat_fields_ui=[
        {"key": "vig", "label": "VIG", "icon": "/icons/er/icon-vigor.png"},
        {"key": "mnd", "label": "MND", "icon": "/icons/er/icon-mind.png"},
        {"key": "end", "label": "END", "icon": "/icons/er/icon-endurance.png"},
        {"key": "str", "label": "STR", "icon": "/icons/er/icon-strength.png"},
        {"key": "dex", "label": "DEX", "icon": "/icons/er/icon-dexterity.png"},
        {"key": "int", "label": "INT", "icon": "/icons/er/icon-intelligence.png"},
        {"key": "fai", "label": "FAI", "icon": "/icons/er/icon-faith.png"},
        {"key": "arc", "label": "ARC", "icon": "/icons/er/icon-arcane.png"},
    ],
    stat_key_map={
        "vig": "vigor",
        "mnd": "mind",
        "end": "endurance",
        "str": "strength",
        "dex": "dexterity",
        "int": "intelligence",
        "fai": "faith",
        "arc": "arcane",
        "main_hand":   "right_weapon_1",
        "off_hand":    "right_weapon_2",
        "left_hand_1": "left_hand_armament_1",
        "left_hand_2": "left_hand_armament_2",
    },
    default_stats={
        "soul_level": "",
        "vig": "", "mnd": "", "end": "",
        "str": "", "dex": "", "int": "", "fai": "", "arc": "",
        "main_hand": "",
        "off_hand": "",
        "left_hand_1": "",
        "left_hand_2": "",
        "build_type": "",
        "current_area": "",
        "last_boss_defeated": "",
        "notes": "",
    },
    local_storage_key="er_player_stats",
    suggested_questions=[
        {"label": "How to start in Limgrave?", "q": "What should I do first in Limgrave as a new player?"},
        {"label": "Best starting class?", "q": "What is the best starting class for a beginner in Elden Ring?"},
        {"label": "How do Ashes of War work?", "q": "How do Ashes of War work and how do I change them?"},
        {"label": "Bleed build guide", "q": "How do I build a bleed/hemorrhage build in Elden Ring?"},
        {"label": "How to beat Malenia?", "q": "How do I beat Malenia, Blade of Miquella?"},
        {"label": "Where to find Smithing Stones?", "q": "Where can I find Smithing Stones to upgrade my weapons?"},
    ],
    slash_commands=[
        {"cmd": "/level", "desc": "Open level-up stat allocator"},
        {"cmd": "/area",  "desc": "Set your current area (e.g. /area Caelid)"},
        {"cmd": "/clear", "desc": "Clear the chat history"},
    ],
    tagline="Seek Your Path to the Erdtree",
    description="AI wiki companion for Elden Ring",
    placeholder_text="Ask the Guide... (Enter to send, Shift+Enter for new line, / for commands)",
    sidebar_right_fields=[
        {"key": "soul_level",        "label": "Level",                 "type": "number"},
        {"key": "main_hand",         "label": "RH Armament 1", "type": "text"},
        {"key": "off_hand",          "label": "RH Armament 2", "type": "text"},
        {"key": "left_hand_1",       "label": "LH Armament 1", "type": "text"},
        {"key": "left_hand_2",       "label": "LH Armament 2", "type": "text"},
        {"key": "build_type",        "label": "Build Type",            "type": "text"},
        {"key": "current_area",      "label": "Current Area",          "type": "text"},
        {"key": "last_boss_defeated","label": "Last Boss",             "type": "text"},
    ],

    # No tier-based matchmaking system in Elden Ring
    soul_memory=None,
)
