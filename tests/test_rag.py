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
    "llama_index.embeddings.huggingface",
]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

_mock_index = MagicMock()
_mock_storage_ctx = MagicMock()
_mock_storage_ctx.from_defaults = MagicMock(return_value=MagicMock())

sys.modules["llama_index.core"].VectorStoreIndex = MagicMock(return_value=_mock_index)
sys.modules["llama_index.core"].SimpleDirectoryReader = MagicMock(return_value=MagicMock())
sys.modules["llama_index.core"].StorageContext = _mock_storage_ctx
sys.modules["llama_index.vector_stores.chroma"].ChromaVectorStore = MagicMock(return_value=MagicMock())
sys.modules["llama_index.embeddings.huggingface"].HuggingFaceEmbedding = MagicMock(return_value=None)

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
