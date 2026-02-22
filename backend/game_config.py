# Game configuration schema for the Scholar companion AI.
# This module defines the data structures that describe a supported game.
# No game-specific data lives here — only the types.
#
# To support a new game, create backend/configs/<game_id>.py that instantiates
# GameConfig with all of the game's data, then import it in the pipeline modules.

from dataclasses import dataclass
from typing import Optional


@dataclass
class SoulMemoryConfig:
    """
    Configuration for a tier-based matchmaking system (DS2 Soul Memory).
    Games that use level-range matchmaking instead should not include this.
    """
    tiers: list            # [(low_sm, high_sm, tier_number), ...]
    max_tier: int          # total number of tiers (len(tiers))
    item_ranges: dict      # {"Item Name": (down_tiers, up_tiers)}
    summary_item: str      # item used for the matchmaking_range summary line


@dataclass
class GameConfig:
    """
    All game-specific configuration for the Scholar RAG pipeline and frontend.
    Instantiate once per supported game (see backend/configs/<game_id>.py).
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    game_id: str           # short slug: "ds2" — used as ChromaDB collection prefix
    game_name: str         # human display name: "Dark Souls 2"
    game_version: str      # edition string: "Scholar of the First Sin (SotFS)"
    bot_name: str          # persona name: "Scholar"
    knowledge_base_dir: str  # absolute path to the .md wiki files

    # ── RAG pipeline ──────────────────────────────────────────────────────────
    system_prompt: str                  # full generation prompt for Claude
    mechanic_term_map: dict             # lowercase trigger → [wiki filenames]
    mechanic_hint_overrides: dict       # trigger → [heading hint words]
    generic_triggers: set               # aggregation triggers to suppress on specific queries
    stat_abbrevs: list                  # [(regex_pattern, expanded_name), ...]
    query_rewriter_game_context: str    # game name injected into the Haiku rewriter prompt
    stop_words_caps: set                # Title-Case words to ignore in entity extraction

    # ── Player stats ──────────────────────────────────────────────────────────
    stat_fields: list      # ordered list of numeric stat backend field names
                           # e.g. ["vigor", "endurance", "vitality", ...]
    stat_labels: dict      # backend_field → display abbreviation
                           # e.g. {"vigor": "VGR", "endurance": "END", ...}
    build_question_words: set  # words that trigger build-context enrichment

    # ── Frontend config (mirrored in frontend/src/gameConfig.js) ─────────────
    stat_fields_ui: list       # [{"key": "vgr", "label": "VGR", "icon": "/icons/..."}, ...]
    stat_key_map: dict         # frontend short key → backend field name
    default_stats: dict        # initial form values (all empty strings)
    local_storage_key: str     # e.g. "ds2_player_stats"
    suggested_questions: list  # [{"label": "...", "q": "..."} | {"label": "...", "action": "..."}]
    slash_commands: list       # [{"cmd": "/level", "desc": "..."}, ...]
    tagline: str
    description: str
    placeholder_text: str

    # ── Optional: sidebar right-column fields ────────────────────────────────
    # [{"key": "soul_level", "label": "Level", "type": "number"}, ...]
    # Drives the right column of the player stats sidebar in App.js.
    # When None, App.js falls back to the DS2 default list (for backwards compat).
    sidebar_right_fields: Optional[list] = None

    # ── Optional: tier-based matchmaking system ───────────────────────────────
    soul_memory: Optional[SoulMemoryConfig] = None
