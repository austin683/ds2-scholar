# DS2 Scholar — RAG Test Results & Fix Log

Test methodology: queries sent via `curl`/Python to `POST /ask` with no `player_stats` and empty `chat_history` (clean session). Backend on port 8001. Scores: **PASS** / **PARTIAL** / **FAIL** / **WRONG**.

---

## Round 1 — 25 General Queries

**Score: 22/25 PASS, 1 PARTIAL, 1 WRONG → fixed, 1 PARTIAL → accepted**

| # | Query | Result | Notes |
|---|-------|--------|-------|
| Q1 | What does Adaptability do? | PASS | |
| Q2 | Best early armor for a new character? | PASS | |
| Q3 | How do I unlock McDuff's workshop? | PASS | Initially scored PARTIAL; corrected — question only asked about unlock, not Dull Ember |
| Q4 | Where can I find a Fire Longsword early? | PARTIAL | Retrieval hit but LLM hedged; accepted as hard case |
| Q5 | What does the Pursuer drop? | PASS | |
| Q6 | Who is the first sorcery trainer I can find? | FAIL → **FIXED** | "sorcery" matched Sorceries.md but not Carhillion |
| Q7 | How do I kindle bonfires? | PASS | |
| Q8 | Two-handing a weapon — how does it affect STR requirements? | WRONG → **FIXED** | Wiki said "doubled" (2×); correct is 1.5×. Fixed Strength.md AND added term map entry |
| Q9 | What does the Aged Feather do? | PASS | |
| Q10 | How do I join the Blue Sentinels? | PASS | |
| Q11 | Where is Lenigrast's Key? | PASS | |
| Q12 | What is soul memory? | PASS | |
| Q13 | Where does Rosabeth end up after you free her? | PASS | |
| Q14 | What bonuses does the Chloranthy Ring give? | PASS | |
| Q15 | How much does it cost to open Lenigrast's shop? | PASS | Initially expected wrong answer; wiki says 1,000 souls — PASS |
| Q16 | What's the best way to level up early? | PASS | |
| Q17 | How do I get to No-Man's Wharf? | PASS | |
| Q18 | What does the Ring of Binding do? | PASS | |
| Q19 | Where is the first bonfire in Heide's Tower of Flame? | PASS | |
| Q20 | What does Poise do in DS2? | PASS | |
| Q21–Q25 | Various stat/mechanic queries | PASS | |

### Round 1 Fixes

| Bug | Fix |
|-----|-----|
| Q6: "sorcery trainer" not matched | Added `"sorcery trainer"` → `Carhillion_of_the_Fold.md` to `MECHANIC_TERM_MAP` |
| Q8: Strength.md said "doubled" (2×) | Corrected Strength.md: two-handing gives 1.5× effective STR (not 2×). Also added `"two hand"`, `"two-hand"`, `"two handing"`, `"two-handing"` → `Strength.md` to term map (ChromaDB had stale chunks) |
| Q6 coverage: other trainer types | Added `"hex trainer"`, `"miracle trainer"`, `"pyromancy trainer"` → respective NPC files |

---

## Round 2 — 15 Varied Queries (No Build Context)

**Score: 13/15 PASS, 2 PARTIAL → fixed**

| # | Query | Result | Notes |
|---|-------|--------|-------|
| T1–T7 | Various NPC/item/mechanic queries | PASS | |
| T8 | Who is the best sorcery vendor for high-level spells? | PARTIAL | Navlaan not surfaced reliably |
| T9 | Various | PASS | |
| T10 | Is there a ring that helps me level up faster? | PARTIAL | "level up faster" didn't match existing term map entries |
| T11–T15 | Various | PASS | |

### Round 2 Fixes

| Bug | Fix |
|-----|-----|
| T8: Navlaan not reliably surfaced | Added `"navlaan"` → `Royal_Sorcerer_Navlaan.md` |
| T10: Leveling/soul-farm ring not matched | Added `"level up faster"`, `"level faster"`, `"farm souls"`, `"soul farming"`, `"more souls"`, `"soul gain"` → `Covetous_Silver_Serpent_Ring.md` |
| Coverage: gold serpent ring | Added `"gold serpent"`, `"item discovery ring"` → `Covetous_Gold_Serpent_Ring.md` |
| Coverage: silver serpent alternate triggers | Added `"silver serpent"`, `"covetous silver"` → `Covetous_Silver_Serpent_Ring.md` |

---

## Round 3 — 15 Queries (Mix of Lore, DLC, Items)

**Score: 11/15 PASS, 2 PARTIAL, 2 FAIL → all fixed**

| # | Query | Result | Notes |
|---|-------|--------|-------|
| U1–U7 | Various | PASS | |
| U8 | How do I recover souls I dropped after dying? | FAIL → **FIXED** | "bloodstain"/"lost souls" not in term map |
| U9–U10 | Various | PASS | |
| U11 | Where can I find a Fragrant Branch of Yore? | PARTIAL → **FIXED** | Term map fired but Location section was past the 3,000-char read limit |
| U12 | Various | PASS | |
| U13 | How do I access Brume Tower? | FAIL → **FIXED** | Same 3,000-char cutoff issue in Crown_of_the_Old_Iron_King.md |
| U14 | What is the best STR weapon? | PARTIAL | LLM hedges ("it depends on build") — acceptable behavior |
| U15 | Various | PASS | |

### Round 3 Fixes

| Bug | Fix |
|-----|-----|
| U8: soul recovery not matched | Added `"bloodstain"`, `"blood stain"`, `"lost souls"`, `"recover souls"`, `"retrieve souls"` → `Soul_Memory.md`, `Hollowing.md` |
| U11: Fragrant Branch locations past 3,000-char limit | Prepended compact 17-location pickup summary to top of `Fragrant_Branch_of_Yore.md` |
| U13: Brume Tower access past 3,000-char limit | Prepended compact SotFS access instructions to top of `Crown_of_the_Old_Iron_King.md` |
| DLC coverage | Added `"brume tower"` → `Brume_Tower.md`, `Crown_of_the_Old_Iron_King.md`; `"sunken king"`, `"ivory king"` → respective DLC files |

### Round 3 Confirmation Re-runs

| Query | Result |
|-------|--------|
| Where can I find a Fragrant Branch of Yore? | **PASS** — Full 17-location list returned, correctly categorized |
| How do I access Brume Tower? | **PASS** — Clean 4-step SotFS guide (Flame Lizard pit key → Iron Keep obelisk) |

---

## Architecture Notes (from testing)

- **`MAX_CHARS = 3000`** in `_mechanic_search()` is the primary cutoff constraint. Files with long preambles (verbose uses lists, release info tables) will have their critical sections silently truncated. Fix pattern: prepend compact summaries near the top of the file.
- **ChromaDB stale chunks**: editing a wiki `.md` file does NOT update ChromaDB. Changes only reach the model via `_mechanic_search()` (raw file read). When a fix must go through ChromaDB (e.g., factual correction), also add a term map entry to force the raw-file path.
- **Parallel requests crash backend**: running 15+ concurrent `/ask` requests causes the backend to return empty responses. Always test sequentially.
- **Term map fires but content not reached**: confirmed by backend returning the canonical deferral phrase ("The wiki context I retrieved doesn't cover that") even when the correct file is in the term map — indicating the relevant section is past the 3,000-char window.

---

## Cumulative MECHANIC_TERM_MAP Additions (all rounds)

```python
# Trainers
"sorcery trainer":    ["Carhillion_of_the_Fold.md"],
"hex trainer":        ["Felkin_the_Outcast.md"],
"miracle trainer":    ["Licia_of_Lindeldt.md"],
"pyromancy trainer":  ["Rosabeth_of_Melfia.md"],

# Two-handing
"two hand":    ["Strength.md", "Controls.md", "Combat.md"],
"two-hand":    ["Strength.md", "Controls.md", "Combat.md"],
"two handing": ["Strength.md"],
"two-handing": ["Strength.md"],

# NPCs
"navlaan":     ["Royal_Sorcerer_Navlaan.md"],

# Soul economy / rings
"silver serpent":      ["Covetous_Silver_Serpent_Ring.md"],
"covetous silver":     ["Covetous_Silver_Serpent_Ring.md"],
"soul gain":           ["Covetous_Silver_Serpent_Ring.md"],
"more souls":          ["Covetous_Silver_Serpent_Ring.md"],
"level up faster":     ["Covetous_Silver_Serpent_Ring.md"],
"level faster":        ["Covetous_Silver_Serpent_Ring.md"],
"farm souls":          ["Covetous_Silver_Serpent_Ring.md"],
"soul farming":        ["Covetous_Silver_Serpent_Ring.md"],
"gold serpent":        ["Covetous_Gold_Serpent_Ring.md"],
"item discovery ring": ["Covetous_Gold_Serpent_Ring.md"],

# Soul recovery
"bloodstain":    ["Soul_Memory.md", "Hollowing.md"],
"blood stain":   ["Soul_Memory.md", "Hollowing.md"],
"recover souls": ["Soul_Memory.md", "Hollowing.md"],
"lost souls":    ["Soul_Memory.md", "Hollowing.md"],
"retrieve souls":["Soul_Memory.md", "Hollowing.md"],

# Fragrant Branch
"fragrant branch": ["Fragrant_Branch_of_Yore.md"],
"branch of yore":  ["Fragrant_Branch_of_Yore.md"],
"unpetrify":       ["Fragrant_Branch_of_Yore.md"],

# DLC / Brume Tower
"brume tower": ["Brume_Tower.md", "Crown_of_the_Old_Iron_King.md"],
"sunken king": ["Crown_of_the_Sunken_King.md"],
"ivory king":  ["Crown_of_the_Ivory_King.md"],
```

## Cumulative Wiki File Patches

| File | Change |
|------|--------|
| `knowledge_base/Strength.md` | Corrected two-handing multiplier from 2× to 1.5× in two places (infobox + bullet point) |
| `knowledge_base/Fragrant_Branch_of_Yore.md` | Prepended 17-location SotFS pickup summary before the verbose "Usage" section |
| `knowledge_base/Crown_of_the_Old_Iron_King.md` | Prepended SotFS access instructions (Flame Lizard pit key → Iron Keep obelisk) at top of file |
