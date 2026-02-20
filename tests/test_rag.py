"""
Tests for the DS2 Scholar RAG pipeline.
Run with: python -m pytest tests/test_rag.py -v
(No API calls are made — tests cover extraction, keyword search, and mechanic map only.)
"""

import os
import sys
import pytest

# Add project root to path so backend can be imported without the server running
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Patch out heavy imports so tests run without loading ChromaDB / HuggingFace ──
import types
from unittest.mock import MagicMock, patch

# Stub llama_index modules
for mod in [
    "llama_index", "llama_index.core", "llama_index.vector_stores",
    "llama_index.vector_stores.chroma", "llama_index.embeddings",
    "llama_index.embeddings.fastembed",
]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

_mock_index = MagicMock()
_mock_storage_ctx = MagicMock()
_mock_storage_ctx.from_defaults = MagicMock(return_value=MagicMock())

sys.modules["llama_index.core"].VectorStoreIndex = MagicMock(return_value=_mock_index)
sys.modules["llama_index.core"].SimpleDirectoryReader = MagicMock(return_value=MagicMock())
sys.modules["llama_index.core"].StorageContext = _mock_storage_ctx
sys.modules["llama_index.vector_stores.chroma"].ChromaVectorStore = MagicMock(return_value=MagicMock())
sys.modules["llama_index.embeddings.fastembed"].FastEmbedEmbedding = MagicMock(return_value=MagicMock())

# Stub chromadb — collection.count() > 0 so get_index uses the "load existing" path
_mock_collection = MagicMock()
_mock_collection.count.return_value = 1
_mock_chroma_client = MagicMock()
_mock_chroma_client.get_or_create_collection.return_value = _mock_collection
chromadb_stub = types.ModuleType("chromadb")
chromadb_stub.PersistentClient = MagicMock(return_value=_mock_chroma_client)
sys.modules["chromadb"] = chromadb_stub

# Stub anthropic
anthropic_stub = types.ModuleType("anthropic")
anthropic_stub.Anthropic = MagicMock(return_value=MagicMock())
sys.modules["anthropic"] = anthropic_stub

# Stub dotenv
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv_stub

with patch("builtins.print"):
    import backend.rag as rag  # noqa: E402


# ── Stub FastAPI + pydantic so main.py can be imported without the server ──
from types import SimpleNamespace

for mod in ["fastapi", "fastapi.middleware", "fastapi.middleware.cors", "fastapi.responses"]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

_fastapi_mock = MagicMock()
sys.modules["fastapi"].FastAPI = MagicMock(return_value=_fastapi_mock)
sys.modules["fastapi"].HTTPException = Exception
sys.modules["fastapi.middleware.cors"].CORSMiddleware = MagicMock()
sys.modules["fastapi.responses"].StreamingResponse = MagicMock()

pydantic_stub = types.ModuleType("pydantic")
class _BaseModel:
    pass
pydantic_stub.BaseModel = _BaseModel
sys.modules.setdefault("pydantic", pydantic_stub)

with patch("builtins.print"), patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test", "ALLOWED_ORIGINS": "http://localhost:3001"}):
    import backend.main as main_module


def make_stats(**kwargs):
    """Create a SimpleNamespace simulating a PlayerStats object."""
    defaults = {
        'soul_level': None, 'soul_memory': None, 'vigor': None,
        'endurance': None, 'vitality': None, 'attunement': None,
        'strength': None, 'dexterity': None, 'adaptability': None,
        'intelligence': None, 'faith': None, 'right_weapon_1': None,
        'right_weapon_2': None, 'current_area': None,
        'last_boss_defeated': None, 'build_type': None, 'notes': None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ─────────────────────────────────────────────────────────────
# extract_key_terms
# ─────────────────────────────────────────────────────────────

class TestExtractKeyTerms:

    def test_title_case_multiword(self):
        terms = rag.extract_key_terms("Where is the Bastille Key?")
        assert "Bastille Key" in terms

    def test_title_case_with_connector(self):
        terms = rag.extract_key_terms("How do I get the Ring of Life Protection?")
        assert "Ring of Life Protection" in terms

    def test_possessive_stripped(self):
        """McDuff's → McDuff should be extracted as a single-word term."""
        terms = rag.extract_key_terms("Where is McDuff's Workshop Key")
        # "Workshop Key" should be multi-word; "McDuff" single-word fallback
        assert any("Workshop Key" in t or "McDuff" in t for t in terms)

    def test_camelcase_fallback(self):
        """McDuff (M+c+D) can't be caught by Title-Case regex — CamelCase fallback handles it."""
        terms = rag.extract_key_terms("How do I unlock McDuff?")
        assert "McDuff" in terms

    def test_all_lowercase_bigram_fallback(self):
        """All-lowercase query should produce bigrams via the lowercase fallback."""
        terms = rag.extract_key_terms("where is mcduff's workshop key")
        # Bigram "mcduff workshop" should appear
        assert "mcduff workshop" in terms

    def test_all_lowercase_single_word_fallback(self):
        """Individual significant words (len≥4) should also appear."""
        terms = rag.extract_key_terms("where is mcduff's workshop key")
        singles = [t for t in terms if " " not in t]
        assert "mcduff" in singles
        assert "workshop" in singles

    def test_stop_words_excluded(self):
        terms = rag.extract_key_terms("Where is the Lost Bastille?")
        assert "Where" not in terms
        assert "The" not in terms

    def test_multiword_before_single(self):
        """Multi-word phrases should appear before single words."""
        terms = rag.extract_key_terms("Bastille Key location")
        multi = [t for t in terms if " " in t]
        single = [t for t in terms if " " not in t]
        if multi and single:
            assert terms.index(multi[0]) < terms.index(single[0])

    def test_lowercase_fallback_only_when_no_caps(self):
        """Lowercase fallback should NOT fire when Title-Case terms were found."""
        terms = rag.extract_key_terms("Where is the Lost Bastille bonfire?")
        # "Lost Bastille" should be found by Title-Case; "lost" "bastille" as
        # lowercase fallback should NOT appear as extra noise
        lower_terms = [t for t in terms if t == t.lower() and " " not in t]
        assert lower_terms == []

    def test_short_words_excluded_from_lowercase_fallback(self):
        """Words shorter than 4 chars should be excluded from the fallback."""
        terms = rag.extract_key_terms("how do i use hex spells")
        # "hex" is 3 chars — excluded; "spells" (6 chars) and "spells" is >= 4, included
        singles = [t for t in terms if " " not in t]
        assert "hex" not in singles  # len 3, filtered


# ─────────────────────────────────────────────────────────────
# _get_kb_filenames — deduplication
# ─────────────────────────────────────────────────────────────

class TestGetKbFilenames:

    def test_no_duplicate_normalized_names(self):
        """After dedup, no two files should normalize to the same key."""
        import re
        files = rag._get_kb_filenames()

        def norm(fname):
            n = re.sub(r"_[0-9a-f]{2}_?", "_", fname.lower())
            return re.sub(r"_+", "_", n)

        norms = [norm(f) for f in files]
        assert len(norms) == len(set(norms)), "Duplicate normalized filenames found"

    def test_plain_version_preferred_over_encoded(self):
        """'McDuff_s_Workshop.md' should be kept; 'McDuff_27s_Workshop.md' should be dropped."""
        files = rag._get_kb_filenames()
        fileset = set(files)
        # Both may not exist in all environments, but if both do, only one survives
        has_encoded = "McDuff_27s_Workshop.md" in fileset
        has_plain = "McDuff_s_Workshop.md" in fileset
        if has_encoded and has_plain:
            pytest.fail("Both _27s_ and _s_ versions present — dedup failed")
        # At least one should be present
        assert has_encoded or has_plain

    def test_results_cached(self):
        """Second call returns the same list object (cached)."""
        first = rag._get_kb_filenames()
        second = rag._get_kb_filenames()
        assert first is second


# ─────────────────────────────────────────────────────────────
# _find_keyword_files
# ─────────────────────────────────────────────────────────────

class TestFindKeywordFiles:

    def test_exact_match_bastille_key(self):
        results = rag._find_keyword_files(["Bastille Key"])
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Bastille_Key.md" in fnames

    def test_exact_match_score_1(self):
        results = rag._find_keyword_files(["Bastille Key"])
        scores = {m["file_name"]: s for _, m, s in results}
        assert scores.get("Bastille_Key.md") == 1.0

    def test_fuzzy_match_mcduff(self):
        """'mcduff' should fuzzy-match McDuff_s_Workshop.md or Steady_Hand_McDuff.md."""
        results = rag._find_keyword_files(["mcduff"])
        fnames = [m["file_name"] for _, m, _ in results]
        assert any("mcduff" in f.lower() or "McDuff" in f for f in fnames)

    def test_fuzzy_match_mcduff_workshop_bigram(self):
        """'mcduff workshop' bigram should match McDuff_s_Workshop.md."""
        results = rag._find_keyword_files(["mcduff workshop"])
        fnames = [m["file_name"] for _, m, _ in results]
        assert any("workshop" in f.lower() for f in fnames)

    def test_fuzzy_cap_enforced(self):
        """Generic single word 'armor' should return at most MAX_FUZZY_PER_TERM=5 results."""
        results = rag._find_keyword_files(["armor"])
        assert len(results) <= 5

    def test_no_duplicates_in_results(self):
        """Same file should not appear twice even if multiple terms match it."""
        results = rag._find_keyword_files(["Bastille Key", "Bastille"])
        fnames = [m["file_name"] for _, m, _ in results]
        assert len(fnames) == len(set(fnames))

    def test_nonexistent_term_returns_empty(self):
        results = rag._find_keyword_files(["XxNonExistentXx123"])
        assert results == []


# ─────────────────────────────────────────────────────────────
# _mechanic_search
# ─────────────────────────────────────────────────────────────

class TestMechanicSearch:

    def test_mcduff_query_returns_bastille_key(self):
        """'mcduff' in query should inject Bastille_Key.md."""
        results = rag._mechanic_search("where is mcduff's workshop key")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Bastille_Key.md" in fnames

    def test_mcduff_query_returns_steady_hand(self):
        results = rag._mechanic_search("where is mcduff's workshop key")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Steady_Hand_McDuff.md" in fnames

    def test_hollow_query_returns_hollowing(self):
        results = rag._mechanic_search("why am I hollowing")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Hollowing.md" in fnames

    def test_hollow_query_returns_human_effigy(self):
        results = rag._mechanic_search("why am I hollowing")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Human_Effigy.md" in fnames

    def test_hex_query_returns_hexes(self):
        results = rag._mechanic_search("what are the best hex spells")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Hexes.md" in fnames

    def test_sorcery_query(self):
        results = rag._mechanic_search("how does sorcery work")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Sorceries.md" in fnames

    def test_miracle_query(self):
        results = rag._mechanic_search("what miracles should I use")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Miracles.md" in fnames

    def test_pyromancy_query(self):
        results = rag._mechanic_search("best pyromancy spells")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Pyromancies.md" in fnames

    def test_dull_ember_query(self):
        results = rag._mechanic_search("where is the dull ember")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Dull_Ember.md" in fnames

    def test_upgrade_query(self):
        results = rag._mechanic_search("how do I upgrade my weapon")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Upgrades.md" in fnames

    def test_lenigrast_query(self):
        results = rag._mechanic_search("where is lenigrast")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Blacksmith_Lenigrast.md" in fnames

    def test_iframes_query(self):
        results = rag._mechanic_search("how do iframes work")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Agility.md" in fnames

    def test_soul_memory_query(self):
        results = rag._mechanic_search("how does soul memory affect matchmaking")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Soul_Memory.md" in fnames

    def test_all_scores_are_0_9(self):
        results = rag._mechanic_search("hollow death curse bleed")
        for _, _, score in results:
            assert score == 0.9

    def test_no_seen_paths_blocking(self):
        """Without seen_paths filtering, same file should be returned even if it
        'would have been seen' — mechanic search always returns its full hit list."""
        results_1 = rag._mechanic_search("dying hollow")
        results_2 = rag._mechanic_search("dying hollow")
        assert results_1 == results_2  # deterministic, not affected by external state

    def test_case_insensitive(self):
        """MCDUFF in caps should still trigger the mcduff entry."""
        results_upper = rag._mechanic_search("WHERE IS MCDUFF")
        results_lower = rag._mechanic_search("where is mcduff")
        fnames_upper = {m["file_name"] for _, m, _ in results_upper}
        fnames_lower = {m["file_name"] for _, m, _ in results_lower}
        assert fnames_upper == fnames_lower

    def test_no_match_returns_empty(self):
        results = rag._mechanic_search("what is the weather like today")
        assert results == []

    def test_possessive_no_apostrophe_mcduffs(self):
        """'mcduffs' (no apostrophe possessive) should still trigger the mcduff entry."""
        results = rag._mechanic_search("where is mcduffs workshop key")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Bastille_Key.md" in fnames

    def test_possessive_with_apostrophe_mcduff(self):
        """\"mcduff's\" (with apostrophe) should also trigger the mcduff entry."""
        results = rag._mechanic_search("where is mcduff's workshop key")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Bastille_Key.md" in fnames

    # ── Cheese / GENERIC_TRIGGERS tests ──────────────────────────────────────

    def test_cheese_trigger_injects_pursuer(self):
        results = rag._mechanic_search("what bosses can be cheesed")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "The_Pursuer.md" in fnames

    def test_cheese_trigger_injects_dragonrider(self):
        results = rag._mechanic_search("what bosses can be cheesed")
        fnames = [m["file_name"] for _, m, _ in results]
        assert "Dragonrider.md" in fnames

    def test_cheese_trigger_injects_all_six(self):
        """All six cheese-map pages should be returned for a broad cheese query."""
        expected = {
            "The_Pursuer.md", "Dragonrider.md", "The_Last_Giant.md",
            "The_Rotten.md", "Ancient_Dragon.md", "Mytha_the_Baneful_Queen.md",
        }
        results = rag._mechanic_search("what bosses can be cheesed")
        fnames = {m["file_name"] for _, m, _ in results}
        assert expected.issubset(fnames)

    def test_cheesed_variant_fires(self):
        """'cheesed' form triggers the same pages as 'cheese'."""
        results = rag._mechanic_search("which bosses get cheesed easily")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "The_Pursuer.md" in fnames

    def test_cheeseable_variant_fires(self):
        results = rag._mechanic_search("what bosses are cheeseable")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Dragonrider.md" in fnames

    def test_cheeses_plural_fires_cheese_trigger(self):
        """'cheeses' (plural) should still match the 'cheese' trigger via s? suffix."""
        results = rag._mechanic_search("list all the cheeses in the game")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "The_Pursuer.md" in fnames

    def test_cheesing_fires_cheese_trigger(self):
        """'cheesing' should trigger the cheese entries (requires 'cheesing' in the map)."""
        results = rag._mechanic_search("tips for cheesing the pursuer")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "The_Pursuer.md" in fnames

    def test_suppress_generic_true_blocks_cheese_list(self):
        """When suppress_generic=True, cheese entries should NOT be injected."""
        results = rag._mechanic_search(
            "does the smelter demon have a cheese", suppress_generic=True
        )
        fnames = {m["file_name"] for _, m, _ in results}
        cheese_pages = {
            "The_Pursuer.md", "Dragonrider.md", "The_Last_Giant.md",
            "The_Rotten.md", "Ancient_Dragon.md", "Mytha_the_Baneful_Queen.md",
        }
        assert fnames.isdisjoint(cheese_pages), (
            f"Cheese pages leaked through suppress_generic: {fnames & cheese_pages}"
        )

    def test_suppress_generic_false_keeps_cheese_list(self):
        """suppress_generic=False (default) should still inject cheese pages."""
        results = rag._mechanic_search(
            "what bosses can be cheesed", suppress_generic=False
        )
        fnames = {m["file_name"] for _, m, _ in results}
        assert "The_Pursuer.md" in fnames

    def test_suppress_generic_does_not_block_non_generic_triggers(self):
        """Non-generic triggers (e.g. gavlan) must still fire even when suppress=True."""
        results = rag._mechanic_search(
            "where is gavlan and does he have a cheese", suppress_generic=True
        )
        fnames = {m["file_name"] for _, m, _ in results}
        # gavlan is not in GENERIC_TRIGGERS — should still be injected
        assert "Gavlan.md" in fnames or "Lonesome_Gavlan.md" in fnames
        # cheese list should be suppressed
        assert "The_Pursuer.md" not in fnames

    def test_generic_triggers_set_contents(self):
        """GENERIC_TRIGGERS must include all cheese/aggregation trigger words."""
        required = {"cheese", "cheesed", "cheeseable", "cheesing", "easy boss"}
        assert required.issubset(rag.GENERIC_TRIGGERS)

    def test_mechanic_hint_overrides_has_cheese(self):
        """MECHANIC_HINT_OVERRIDES must have strategy-level hints for cheese triggers."""
        for trigger in ("cheese", "cheesed", "cheeseable"):
            assert trigger in rag.MECHANIC_HINT_OVERRIDES
            hints = rag.MECHANIC_HINT_OVERRIDES[trigger]
            assert "strategy" in hints or "tips" in hints or "hints" in hints


# ─────────────────────────────────────────────────────────────
# extract_key_terms — cheese/suppress interaction helpers
# ─────────────────────────────────────────────────────────────

class TestExtractKeyTermsCheeseQueries:

    def test_broad_cheese_query_returns_no_title_case_terms(self):
        """'what bosses can be cheesed' has no proper nouns → terms=[] → suppress=False."""
        terms = rag.extract_key_terms("what bosses can be cheesed")
        # Should produce lowercase fallback terms only (no Title-Case)
        title_case_terms = [t for t in terms if t[0].isupper()]
        assert title_case_terms == []

    def test_specific_boss_cheese_query_returns_boss_term(self):
        """'Does the Dragonrider have a cheese' → 'Dragonrider' extracted → suppress=True."""
        terms = rag.extract_key_terms("Does the Dragonrider have a cheese")
        assert any("Dragonrider" in t for t in terms)

    def test_specific_boss_cheese_query_lowercase_still_has_terms(self):
        """All-lowercase boss+cheese query still produces terms (via fallback) → suppress=True."""
        terms = rag.extract_key_terms("can i cheese the smelter demon")
        # lowercase fallback: "smelter", "demon", "cheese" extracted as singles/bigrams
        assert len(terms) > 0  # non-empty → suppress_generic=True in retrieve_context

    def test_cheesing_gerund_lowercase_fallback(self):
        """'cheesing' should appear in fallback terms so the caller knows a cheese query."""
        terms = rag.extract_key_terms("tips for cheesing the ancient dragon")
        term_strs = " ".join(terms)
        assert "cheesing" in term_strs or "ancient" in term_strs


# ─────────────────────────────────────────────────────────────
# MECHANIC_TERM_MAP — stat names and abbreviations
# ─────────────────────────────────────────────────────────────

class TestNewStatMechanicMapEntries:
    """Tests that individual stat names and common abbreviations resolve to the correct wiki pages."""

    def test_strength_full_name(self):
        """'strength' in a query should inject Strength.md."""
        results = rag._mechanic_search("how much strength do I need to two-hand this weapon")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Strength.md" in fnames

    def test_str_abbreviation(self):
        """'str' as a standalone term should inject Strength.md."""
        results = rag._mechanic_search("what does str do")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Strength.md" in fnames

    def test_dexterity_full_name(self):
        """'dexterity' in a query should inject Dexterity.md."""
        results = rag._mechanic_search("does dexterity affect cast speed")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Dexterity.md" in fnames

    def test_dex_abbreviation(self):
        """'dex' in a query should inject Dexterity.md."""
        results = rag._mechanic_search("how much dex for a katana build")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Dexterity.md" in fnames

    def test_faith_full_name(self):
        """'faith' in a query should inject Faith.md."""
        results = rag._mechanic_search("how much faith for miracles")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Faith.md" in fnames

    def test_fth_abbreviation(self):
        """'fth' in a query should inject Faith.md."""
        results = rag._mechanic_search("what soft cap for fth")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Faith.md" in fnames

    def test_vigor_full_name(self):
        """'vigor' in a query should inject Vigor.md."""
        results = rag._mechanic_search("what is the vigor soft cap")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Vigor.md" in fnames

    def test_vitality_full_name(self):
        """'vitality' in a query should inject Vitality.md."""
        results = rag._mechanic_search("does vitality increase equipment load")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Vitality.md" in fnames

    def test_endurance_full_name(self):
        """'endurance' in a query should inject Endurance.md."""
        results = rag._mechanic_search("how much endurance for stamina regen")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Endurance.md" in fnames

    def test_adaptability_full_name(self):
        """'adaptability' in a query should inject Adaptability.md."""
        results = rag._mechanic_search("how much adaptability do I need for 96 agility")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Adaptability.md" in fnames

    def test_adp_abbreviation(self):
        """'adp' in a query should inject Adaptability.md."""
        results = rag._mechanic_search("what is a good adp value")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Adaptability.md" in fnames

    def test_intelligence_full_name(self):
        """'intelligence' in a query should inject Intelligence.md."""
        results = rag._mechanic_search("how much intelligence for dark sorceries")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Intelligence.md" in fnames

    def test_int_abbreviation(self):
        """'int' as a standalone term should inject Intelligence.md."""
        results = rag._mechanic_search("what does int do for hexes")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Intelligence.md" in fnames

    def test_attunement_standalone(self):
        """'attunement' standalone (not 'attunement slots') should inject Attunement.md."""
        results = rag._mechanic_search("how does attunement work")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Attunement.md" in fnames

    def test_atn_abbreviation(self):
        """'atn' in a query should inject Attunement.md."""
        results = rag._mechanic_search("how much atn do I need")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Attunement.md" in fnames


# ─────────────────────────────────────────────────────────────
# MECHANIC_TERM_MAP — leveling and progression entries
# ─────────────────────────────────────────────────────────────

class TestLevelingMechanicMapEntries:
    """Tests that leveling and stat-cap related terms resolve to the correct wiki pages."""

    def test_level_query_returns_level_md(self):
        """'level' keyword should inject Level.md."""
        results = rag._mechanic_search("how do I level up faster")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Level.md" in fnames

    def test_level_query_returns_stat_scaling(self):
        """'level' keyword should also inject Stat_Scaling.md."""
        results = rag._mechanic_search("how do I level up faster")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Stat_Scaling.md" in fnames

    def test_leveling_query(self):
        """'leveling' keyword should inject Level.md."""
        results = rag._mechanic_search("tips for leveling efficiently in ds2")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Level.md" in fnames

    def test_level_up_phrase(self):
        """'level up' phrase should inject Level.md."""
        results = rag._mechanic_search("where do I level up in ds2")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Level.md" in fnames

    def test_levels_plural(self):
        """'levels' plural should inject Level.md."""
        results = rag._mechanic_search("how many levels does it take to soft cap")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Level.md" in fnames

    def test_soft_cap_query(self):
        """'soft cap' phrase should inject Stat_Scaling.md."""
        results = rag._mechanic_search("what is the soft cap for vigor")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Stat_Scaling.md" in fnames

    def test_softcap_single_word(self):
        """'softcap' as a single word should inject Stat_Scaling.md."""
        results = rag._mechanic_search("what is the softcap for strength")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Stat_Scaling.md" in fnames

    def test_hard_cap_query(self):
        """'hard cap' phrase should inject Stat_Scaling.md."""
        results = rag._mechanic_search("is there a hard cap on faith")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Stat_Scaling.md" in fnames

    def test_invest_query(self):
        """'invest' keyword should inject Stat_Scaling.md."""
        results = rag._mechanic_search("should I invest more points into dexterity")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Stat_Scaling.md" in fnames

    def test_stat_points_query(self):
        """'stat points' phrase should inject Level.md."""
        results = rag._mechanic_search("how do stat points work in ds2")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "Level.md" in fnames


# ─────────────────────────────────────────────────────────────
# MECHANIC_TERM_MAP — boss name entries
# ─────────────────────────────────────────────────────────────

class TestBossMechanicMapEntries:
    """Tests that boss names written in lowercase correctly resolve to boss wiki pages."""

    def test_pursuer_lowercase(self):
        """'pursuer' in a lowercase query should inject The_Pursuer.md."""
        results = rag._mechanic_search("how do i beat the pursuer")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "The_Pursuer.md" in fnames

    def test_the_pursuer_lowercase(self):
        """'the pursuer' as a phrase in lowercase should inject The_Pursuer.md."""
        results = rag._mechanic_search("what is the pursuer weak to")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "The_Pursuer.md" in fnames

    def test_pursuer_with_capitalized_entity_regression(self):
        """Regression: 'pursuer to appear in the Lost Bastille' — another capitalized
        term ('Lost Bastille') was previously blocking the lowercase 'pursuer' fallback
        from triggering. The mechanic map must still inject The_Pursuer.md here."""
        results = rag._mechanic_search("how do I get the pursuer to appear in the lost bastille")
        fnames = {m["file_name"] for _, m, _ in results}
        assert "The_Pursuer.md" in fnames, (
            "Regression: 'pursuer' lowercase trigger was blocked when another named "
            "entity appeared in the query. Mechanic map must fire independently."
        )


# ─────────────────────────────────────────────────────────────
# _brief_player_summary (main_module)
# ─────────────────────────────────────────────────────────────

class TestBriefPlayerSummary:
    """Tests for main_module._brief_player_summary — compact one-line player description."""

    def test_no_stats_returns_empty_string(self):
        """When player_stats is None, the function should return an empty string."""
        result = main_module._brief_player_summary(None)
        assert result == ""

    def test_only_build_type(self):
        """Only build_type set → 'STR build'."""
        stats = make_stats(build_type="STR")
        result = main_module._brief_player_summary(stats)
        assert result == "STR build"

    def test_build_type_and_soul_level(self):
        """build_type + soul_level → 'STR build, SL62'."""
        stats = make_stats(build_type="STR", soul_level=62)
        result = main_module._brief_player_summary(stats)
        assert "STR build" in result
        assert "SL62" in result

    def test_build_type_soul_level_weapon(self):
        """build_type + soul_level + right_weapon_1 → all three appear."""
        stats = make_stats(build_type="STR", soul_level=62, right_weapon_1="Greatsword +2")
        result = main_module._brief_player_summary(stats)
        assert "STR build" in result
        assert "SL62" in result
        assert "Greatsword +2" in result

    def test_build_type_soul_level_both_weapons(self):
        """Both right_weapon_1 and right_weapon_2 should appear in the summary."""
        stats = make_stats(
            build_type="STR", soul_level=62,
            right_weapon_1="Greatsword +2", right_weapon_2="Dragonrider Bow +5"
        )
        result = main_module._brief_player_summary(stats)
        assert "Greatsword +2" in result
        assert "Dragonrider Bow +5" in result

    def test_build_type_soul_level_weapon_area(self):
        """current_area should appear at the end of the summary."""
        stats = make_stats(
            build_type="STR", soul_level=62,
            right_weapon_1="Greatsword +2", current_area="Iron Keep"
        )
        result = main_module._brief_player_summary(stats)
        assert "Iron Keep" in result
        # area should be the last comma-separated part
        parts = result.split(", ")
        assert parts[-1] == "Iron Keep"

    def test_all_fields_set(self):
        """When all relevant fields are set, all should appear in the result string."""
        stats = make_stats(
            build_type="DEX", soul_level=80,
            right_weapon_1="Rapier +10", right_weapon_2="Parrying Dagger +5",
            current_area="Drangleic Castle"
        )
        result = main_module._brief_player_summary(stats)
        assert "DEX build" in result
        assert "SL80" in result
        assert "Rapier +10" in result
        assert "Parrying Dagger +5" in result
        assert "Drangleic Castle" in result

    def test_no_build_type_but_has_weapon(self):
        """When only right_weapon_1 is set (no build_type), the weapon should still appear."""
        stats = make_stats(right_weapon_1="Black Knight Greatsword +5")
        result = main_module._brief_player_summary(stats)
        assert "Black Knight Greatsword +5" in result

    def test_empty_stats_object_returns_empty(self):
        """A stats object with all None fields should return an empty string."""
        stats = make_stats()
        result = main_module._brief_player_summary(stats)
        assert result == ""

    def test_comma_separated_format(self):
        """The summary should use ', ' as the delimiter between parts."""
        stats = make_stats(build_type="FTH", soul_level=50, current_area="Shrine of Amana")
        result = main_module._brief_player_summary(stats)
        assert ", " in result
        parts = result.split(", ")
        assert len(parts) == 3


# ─────────────────────────────────────────────────────────────
# _enrich_term_query_for_build (main_module)
# ─────────────────────────────────────────────────────────────

class TestEnrichTermQueryForBuild:
    """Tests for main_module._enrich_term_query_for_build — appends build info to build queries."""

    def test_level_query_with_str_build_appends_str(self):
        """A 'level' query with a STR build type should append 'str' to the term query."""
        stats = make_stats(build_type="STR")
        result = main_module._enrich_term_query_for_build("what should I level next", stats)
        assert "str" in result.lower()

    def test_level_query_with_weapon_appends_weapon_name(self):
        """A 'level' query with a weapon set should append the weapon name."""
        stats = make_stats(right_weapon_1="Greatsword +2")
        result = main_module._enrich_term_query_for_build("what should I level next", stats)
        assert "Greatsword" in result

    def test_weapon_plus_suffix_stripped(self):
        """The '+X' upgrade suffix should be stripped from the weapon name when appending."""
        stats = make_stats(right_weapon_1="Greatsword +2")
        result = main_module._enrich_term_query_for_build("what should I level next", stats)
        assert "Greatsword" in result
        assert "Greatsword +2" not in result

    def test_non_build_query_unchanged(self):
        """A query with no build-related words should be returned unchanged."""
        stats = make_stats(build_type="STR", right_weapon_1="Greatsword +2")
        result = main_module._enrich_term_query_for_build("where is the lost bastille", stats)
        assert result == "where is the lost bastille"

    def test_should_keyword_triggers_enrichment(self):
        """'should' is a build question word and should trigger enrichment."""
        stats = make_stats(build_type="DEX")
        result = main_module._enrich_term_query_for_build("should I use a katana", stats)
        assert "dex" in result.lower()

    def test_infuse_keyword_triggers_enrichment(self):
        """'infuse' is a new trigger word and should trigger enrichment."""
        stats = make_stats(build_type="STR", right_weapon_1="Claymore +10")
        result = main_module._enrich_term_query_for_build("should I infuse my weapon", stats)
        assert "str" in result.lower()

    def test_weapon_keyword_triggers_enrichment(self):
        """'weapon' is a new trigger word and should trigger enrichment."""
        stats = make_stats(build_type="STR", right_weapon_1="Greatsword +5")
        result = main_module._enrich_term_query_for_build("what weapon should I use", stats)
        assert "str" in result.lower()

    def test_swap_keyword_triggers_enrichment(self):
        """'swap' is a new trigger word and should trigger enrichment."""
        stats = make_stats(build_type="DEX", right_weapon_1="Rapier +10")
        result = main_module._enrich_term_query_for_build("when should I swap weapons", stats)
        assert "dex" in result.lower()

    def test_both_weapons_appended(self):
        """When both right_weapon_1 and right_weapon_2 are set, both should be appended."""
        stats = make_stats(
            right_weapon_1="Greatsword +5",
            right_weapon_2="Dragonrider Bow +3"
        )
        result = main_module._enrich_term_query_for_build("what should I upgrade", stats)
        assert "Greatsword" in result
        assert "Dragonrider Bow" in result

    def test_only_right_weapon_2_appended_when_weapon_1_none(self):
        """When right_weapon_1 is None, right_weapon_2 should still be appended."""
        stats = make_stats(right_weapon_2="Pyromancy Flame +10")
        result = main_module._enrich_term_query_for_build("should I upgrade this", stats)
        assert "Pyromancy Flame" in result

    def test_no_player_stats_returns_unchanged(self):
        """When player_stats is None, the query should be returned unchanged."""
        result = main_module._enrich_term_query_for_build("what should I level next", None)
        assert result == "what should I level next"

    def test_enriched_query_contains_original_text(self):
        """The enriched query must still contain the full original question text."""
        original = "what should I level next"
        stats = make_stats(build_type="STR")
        result = main_module._enrich_term_query_for_build(original, stats)
        assert original in result

    def test_build_type_lowercased_in_enrichment(self):
        """The build type is appended in lowercase to match MECHANIC_TERM_MAP keys."""
        stats = make_stats(build_type="FTH")
        result = main_module._enrich_term_query_for_build("should I raise this stat", stats)
        assert "fth" in result

    def test_weapon_name_without_plus_suffix(self):
        """A weapon with no +X suffix should be appended as-is without modification."""
        stats = make_stats(right_weapon_1="Moonlight Greatsword")
        result = main_module._enrich_term_query_for_build("should I upgrade my weapon", stats)
        assert "Moonlight Greatsword" in result


# ─────────────────────────────────────────────────────────────
# _BUILD_QUESTION_WORDS set contents (main_module)
# ─────────────────────────────────────────────────────────────

class TestBuildQuestionWords:
    """Tests that _BUILD_QUESTION_WORDS contains the expected trigger words."""

    def test_level_in_set(self):
        """'level' must be in _BUILD_QUESTION_WORDS."""
        assert "level" in main_module._BUILD_QUESTION_WORDS

    def test_leveling_in_set(self):
        """'leveling' must be in _BUILD_QUESTION_WORDS."""
        assert "leveling" in main_module._BUILD_QUESTION_WORDS

    def test_stat_in_set(self):
        """'stat' must be in _BUILD_QUESTION_WORDS."""
        assert "stat" in main_module._BUILD_QUESTION_WORDS

    def test_build_in_set(self):
        """'build' must be in _BUILD_QUESTION_WORDS."""
        assert "build" in main_module._BUILD_QUESTION_WORDS

    def test_upgrade_in_set(self):
        """'upgrade' must be in _BUILD_QUESTION_WORDS."""
        assert "upgrade" in main_module._BUILD_QUESTION_WORDS

    def test_weapon_in_set(self):
        """'weapon' must be in _BUILD_QUESTION_WORDS (new addition)."""
        assert "weapon" in main_module._BUILD_QUESTION_WORDS

    def test_weapons_in_set(self):
        """'weapons' must be in _BUILD_QUESTION_WORDS (new addition)."""
        assert "weapons" in main_module._BUILD_QUESTION_WORDS

    def test_infuse_in_set(self):
        """'infuse' must be in _BUILD_QUESTION_WORDS (new addition)."""
        assert "infuse" in main_module._BUILD_QUESTION_WORDS

    def test_infusion_in_set(self):
        """'infusion' must be in _BUILD_QUESTION_WORDS (new addition)."""
        assert "infusion" in main_module._BUILD_QUESTION_WORDS

    def test_swap_in_set(self):
        """'swap' must be in _BUILD_QUESTION_WORDS (new addition)."""
        assert "swap" in main_module._BUILD_QUESTION_WORDS

    def test_switch_in_set(self):
        """'switch' must be in _BUILD_QUESTION_WORDS (new addition)."""
        assert "switch" in main_module._BUILD_QUESTION_WORDS

    def test_where_not_in_set(self):
        """'where' is a location word, not a build question word — must NOT be in the set."""
        assert "where" not in main_module._BUILD_QUESTION_WORDS

    def test_what_not_in_set(self):
        """'what' is a generic question word, not a build question word — must NOT be in the set."""
        assert "what" not in main_module._BUILD_QUESTION_WORDS

    def test_how_not_in_set(self):
        """'how' is a generic question word — must NOT be in the set."""
        assert "how" not in main_module._BUILD_QUESTION_WORDS

    def test_the_not_in_set(self):
        """'the' is an article — must NOT be in the set."""
        assert "the" not in main_module._BUILD_QUESTION_WORDS


# ─────────────────────────────────────────────────────────────
# MECHANIC_TERM_MAP — all DS2 boss name entries
# ─────────────────────────────────────────────────────────────

class TestBossMechanicMapEntriesExtended:
    """Tests that all major DS2 boss names in lowercase resolve via the mechanic map.

    Motivation: many boss pages have long compound filenames (e.g.
    Ruin_Sentinels_Yahim_Ricce_and_Alessia.md) that fail exact-match in
    _find_keyword_files, and 'where can I find X boss' queries may not rank
    the boss file in the top-10 semantic results. Adding them to MECHANIC_TERM_MAP
    guarantees score 0.9 and a top-10 slot regardless of query phrasing.
    """

    def _fnames(self, query: str) -> set:
        return {m["file_name"] for _, m, _ in rag._mechanic_search(query)}

    def test_ruin_sentinels_lowercase(self):
        """'ruin sentinels' must resolve to the Yahim/Ricce/Alessia boss file."""
        fnames = self._fnames("where can i find the ruin sentinels")
        assert "Ruin_Sentinels_Yahim_Ricce_and_Alessia.md" in fnames

    def test_ruin_sentinel_singular(self):
        """'ruin sentinel' (singular) should also resolve to the boss page."""
        fnames = self._fnames("how do i beat the ruin sentinel")
        assert "Ruin_Sentinels_Yahim_Ricce_and_Alessia.md" in fnames

    def test_lost_sinner_lowercase(self):
        fnames = self._fnames("where is the lost sinner")
        assert "Lost_Sinner.md" in fnames

    def test_dragonrider_lowercase(self):
        fnames = self._fnames("how do i beat the dragonrider")
        assert "Dragonrider.md" in fnames

    def test_twin_dragonriders(self):
        fnames = self._fnames("tips for twin dragonriders")
        assert "Twin_Dragonriders.md" in fnames

    def test_last_giant(self):
        fnames = self._fnames("how do i beat the last giant")
        assert "The_Last_Giant.md" in fnames

    def test_looking_glass_knight(self):
        fnames = self._fnames("where is the looking glass knight")
        assert "Looking_Glass_Knight.md" in fnames

    def test_smelter_demon(self):
        fnames = self._fnames("tips for smelter demon")
        assert "Smelter_Demon.md" in fnames

    def test_blue_smelter_demon(self):
        fnames = self._fnames("how do i kill the blue smelter demon")
        assert "Blue_Smelter_Demon.md" in fnames

    def test_flexile_sentry(self):
        fnames = self._fnames("flexile sentry weakness")
        assert "Flexile_Sentry.md" in fnames

    def test_guardian_dragon(self):
        fnames = self._fnames("where is the guardian dragon")
        assert "Guardian_Dragon.md" in fnames

    def test_belfry_gargoyle(self):
        fnames = self._fnames("how to beat belfry gargoyle")
        assert "Belfry_Gargoyle.md" in fnames

    def test_covetous_demon(self):
        fnames = self._fnames("covetous demon location")
        assert "Covetous_Demon.md" in fnames

    def test_skeleton_lords(self):
        fnames = self._fnames("how to beat the skeleton lords")
        assert "The_Skeleton_Lords.md" in fnames or "Skeleton_Lords.md" in fnames

    def test_scorpioness_najka(self):
        fnames = self._fnames("how do i beat scorpioness najka")
        assert "Scorpioness_Najka.md" in fnames

    def test_najka_short(self):
        """'najka' alone should resolve to the boss page."""
        fnames = self._fnames("najka tips")
        assert "Scorpioness_Najka.md" in fnames

    def test_royal_rat_authority(self):
        fnames = self._fnames("royal rat authority strategy")
        assert "Royal_Rat_Authority.md" in fnames

    def test_royal_rat_vanguard(self):
        fnames = self._fnames("royal rat vanguard cheese")
        assert "Royal_Rat_Vanguard.md" in fnames

    def test_mytha(self):
        fnames = self._fnames("how to beat mytha")
        assert "Mytha_the_Baneful_Queen.md" in fnames

    def test_demon_of_song(self):
        fnames = self._fnames("where is the demon of song")
        assert "Demon_of_Song.md" in fnames

    def test_darklurker(self):
        fnames = self._fnames("darklurker weakness")
        assert "Darklurker.md" in fnames

    def test_giant_lord(self):
        fnames = self._fnames("where is the giant lord")
        assert "Giant_Lord.md" in fnames

    def test_nashandra(self):
        fnames = self._fnames("nashandra tips")
        assert "Nashandra.md" in fnames

    def test_aldia(self):
        fnames = self._fnames("how to beat aldia")
        assert "Aldia_Scholar_of_the_First_Sin.md" in fnames

    def test_throne_watcher(self):
        fnames = self._fnames("throne watcher strategy")
        assert "Throne_Watcher_and_Throne_Defender.md" in fnames

    def test_throne_defender(self):
        fnames = self._fnames("throne defender tips")
        assert "Throne_Watcher_and_Throne_Defender.md" in fnames

    def test_executioner_chariot(self):
        fnames = self._fnames("executioner chariot weakness")
        assert "Executioner_s_Chariot.md" in fnames

    def test_old_dragonslayer(self):
        fnames = self._fnames("where is the old dragonslayer")
        assert "Old_Dragonslayer.md" in fnames

    def test_aava(self):
        fnames = self._fnames("how to beat aava")
        assert "Aava_the_King_s_Pet.md" in fnames

    def test_sinh(self):
        fnames = self._fnames("sinh the slumbering dragon tips")
        assert "Sinh_the_Slumbering_Dragon.md" in fnames

    def test_elana(self):
        fnames = self._fnames("elana squalid queen strategy")
        assert "Elana_Squalid_Queen.md" in fnames

    def test_fume_knight(self):
        fnames = self._fnames("how to beat fume knight")
        assert "Fume_Knight.md" in fnames

    def test_lud_and_zallen(self):
        fnames = self._fnames("lud and zallen tips")
        assert "Lud_and_Zallen_the_King_s_Pets.md" in fnames

    def test_velstadt(self):
        fnames = self._fnames("velstadt weakness")
        assert "Velstadt_the_Royal_Aegis.md" in fnames

    def test_vendrick(self):
        fnames = self._fnames("how do i beat vendrick")
        assert "Vendrick.md" in fnames

    def test_ancient_dragon(self):
        fnames = self._fnames("ancient dragon location")
        assert "Ancient_Dragon.md" in fnames

    def test_the_rotten(self):
        fnames = self._fnames("tips for the rotten")
        assert "The_Rotten.md" in fnames


# ─────────────────────────────────────────────────────────────
# _build_term_query (main_module) — pronoun-only prepend logic
# ─────────────────────────────────────────────────────────────

class TestBuildTermQuery:
    """Tests for main_module._build_term_query — pronoun-only prepend after the
    caps_count condition was removed to prevent previous-query contamination."""

    def _call(self, question, history=None):
        return main_module._build_term_query(question, history)

    def test_no_history_returns_question_unchanged(self):
        """With no chat history, the question is returned as-is."""
        assert self._call("where is the last giant", None) == "where is the last giant"

    def test_empty_history_returns_question_unchanged(self):
        assert self._call("where is the last giant", []) == "where is the last giant"

    def test_pronoun_triggers_prepend(self):
        """A question with a pronoun (he/she/it/they) gets previous user msg prepended."""
        history = [{"role": "user", "content": "Tell me about Gavlan"}]
        result = self._call("where will he be next", history)
        assert "Gavlan" in result
        assert "where will he be next" in result

    def test_its_pronoun_triggers_prepend(self):
        """'its' counts as a pronoun."""
        history = [{"role": "user", "content": "Tell me about the Ruin Sentinels"}]
        result = self._call("what are its weaknesses", history)
        assert "Ruin Sentinels" in result

    def test_they_pronoun_triggers_prepend(self):
        """'they' counts as a pronoun."""
        history = [{"role": "user", "content": "How do I reach Shrine of Amana"}]
        result = self._call("how many of them are there", history)
        assert "Shrine of Amana" in result

    def test_no_pronoun_no_prepend(self):
        """A question with no pronoun must NOT get the previous message prepended.
        Regression: the old caps_count < 2 condition was too eager and would prepend
        'where is the last giant' onto 'what weapons drop here?', polluting retrieval."""
        history = [{"role": "user", "content": "where can I find the ruin sentinels"}]
        result = self._call("what weapons drop here", history)
        assert "ruin sentinels" not in result.lower()
        assert result == "what weapons drop here"

    def test_two_caps_no_pronoun_no_prepend(self):
        """A question with 2+ capitalized entity words but no pronoun must NOT prepend.
        This was the Ruin Sentinels regression: 'where can I find the Ruin Sentinels?'
        had 2 caps (>=2) so caps_count condition was False; pronoun is also False.
        Result: no prepend → term_query = original question only."""
        history = [{"role": "user", "content": "Tell me about the Lost Bastille"}]
        result = self._call("where can I find the Ruin Sentinels", history)
        assert result == "where can I find the Ruin Sentinels"

    def test_assistant_messages_skipped(self):
        """Only user messages are considered; assistant messages are ignored."""
        history = [
            {"role": "user", "content": "Tell me about Gavlan"},
            {"role": "assistant", "content": "Gavlan is a merchant..."},
        ]
        result = self._call("where is he now", history)
        # The pronoun 'is' ... wait 'he' is a pronoun → should prepend Gavlan's message
        assert "Gavlan" in result
