# RAG (Retrieval-Augmented Generation) pipeline for the Scholar companion AI.
# Handles loading the knowledge base into ChromaDB, embedding queries,
# retrieving relevant documents, and generating answers via the Anthropic API.
# Game-specific data (MECHANIC_TERM_MAP, SYSTEM_PROMPT, etc.) is loaded from
# the active game config selected by the GAME_ID env var (default: "ds2").
# Supported: GAME_ID=ds2 → backend/configs/ds2.py, GAME_ID=er → backend/configs/er.py

import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.fastembed import FastEmbedEmbedding
import chromadb
import anthropic

load_dotenv()

from backend.configs.ds2 import DS2_CONFIG
from backend.configs.er import ER_CONFIG
_ALL_CONFIGS: dict = {"ds2": DS2_CONFIG, "er": ER_CONFIG}
_CONFIG = DS2_CONFIG  # kept for backwards-compat module-level aliases

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_BASE_DIR = DS2_CONFIG.knowledge_base_dir  # backwards-compat; use config.knowledge_base_dir per request
DB_DIR = os.path.join(BASE_DIR, "db")
DB_BAKED_DIR = os.path.join(BASE_DIR, "db_baked")  # pre-built index baked into Docker image

# Anthropic client
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


@lru_cache(maxsize=256)
def rewrite_query_for_retrieval(question: str, game_id: str = "ds2", brief_stats: str = "") -> str:
    """
    Use Claude Haiku to convert a user question into retrieval keywords for the
    given game.  game_id is a string (hashable) so lru_cache works correctly.

    The output is appended to the original question so the existing heuristics
    (extract_key_terms, mechanic map) still fire on the original phrasing, while
    the rewritten keywords improve recall for vague or lowercase queries.

    brief_stats: compact player summary, e.g. "STR build, SL62, Greatsword +2, Lost Bastille"
    Falls back to the original question if the Haiku call fails.
    """
    cfg = _ALL_CONFIGS.get(game_id, DS2_CONFIG)
    stats_note = f"\nPlayer: {brief_stats}" if brief_stats else ""
    try:
        response = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": (
                    f"Convert this {cfg.query_rewriter_game_context} question into wiki search keywords. "
                    f"Output ONLY space-separated terms: entity names, stat names, mechanic terms, wiki page names. "
                    f"No explanation, no punctuation, no full sentences.{stats_note}\n\nQuestion: {question}"
                ),
            }],
        )
        keywords = response.content[0].text.strip()
        return f"{question} {keywords}"
    except Exception:
        return question

# ─── TWO DATA-PATH ARCHITECTURE ──────────────────────────────────────────────
# retrieve_context() uses two independent ways to read knowledge_base/ content:
#
#   PATH A — ChromaDB vector index (semantic search)
#     • Built once by get_index() from the .md files, stored under db/.
#     • NEVER reflects file edits made after the index was last built.
#     • Must be rebuilt (scripts/rebuild_index.py) to pick up changes.
#
#   PATH B — raw .md file reads (_mechanic_search, _find_keyword_files)
#     • Always reads the current file on disk; reflects edits immediately.
#     • But only returns a window of FILE_READ_MAX_CHARS per file.
#
# Consequence: editing a .md file fixes PATH B instantly but PATH A stays
# stale until the index is rebuilt. On startup we warn if stale files are
# detected (see _check_index_freshness). Use scripts/rebuild_index.py to sync.
# ─────────────────────────────────────────────────────────────────────────────

# Maximum characters read from a single file in PATH B (keyword / mechanic search).
# Section-aware truncation in _read_file_section keeps this from cutting mid-section.
FILE_READ_MAX_CHARS = 5000

# Timestamp file written when the index is freshly built; used for stale detection.
INDEX_TIMESTAMP_FILE = os.path.join(DB_DIR, ".index_built_at")

# Use a free local embedding model — no OpenAI needed
EMBED_MODEL = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Per-game caches — keyed by game_id so DS2 and ER never share cache slots.
_KB_FILENAMES: dict = {}    # game_id → list[str]
_RETRIEVE_CACHE: dict = {}  # game_id → {(query, top_k, brief_stats): str}
_RETRIEVE_CACHE_MAX = 256
_FNAME_LOOKUP: dict = {}    # game_id → {norm_name: fname}


def _norm_fname(fname: str) -> str:
    """
    Normalize a filename for deduplication.
    Collapses URL-encoding (_27_ → _) and repeated underscores so both
    encoded and plain variants of the same file map to the same key.
    e.g. "No_Man_27s_Wharf.md" and "No_Man_s_Wharf.md" → same key.
    """
    n = re.sub(r"_[0-9a-f]{2}_?", "_", fname.lower())
    return re.sub(r"_+", "_", n)


def _get_kb_filenames(config=None) -> list:
    """
    Return a cached, deduplicated list of .md filenames for the given game's
    knowledge base.  config defaults to DS2_CONFIG for backwards compat.

    The scraper saved many pages twice — once with URL-encoded apostrophes/commas
    (e.g. "McDuff_27s_Workshop.md", "Aava_2C_the_King_27s_Pet.md") and once with
    plain separators ("McDuff_s_Workshop.md", "Aava_the_King_s_Pet.md").
    We keep the alphabetically-later (plain) version and discard the _XX_ variant
    so duplicate content doesn't waste top_k context slots.
    """
    cfg = config if config is not None else DS2_CONFIG
    gid = cfg.game_id
    if gid not in _KB_FILENAMES:
        all_files = [f for f in os.listdir(cfg.knowledge_base_dir) if f.endswith(".md")]
        seen: dict = {}  # norm_key → fname; later (alphabetically) wins
        for fname in sorted(all_files):
            seen[_norm_fname(fname)] = fname  # plain _s_ sorts after _27s_, so it wins
        _KB_FILENAMES[gid] = list(seen.values())
    return _KB_FILENAMES[gid]


# ── Game-config aliases ───────────────────────────────────────────────────────
# These module-level names are imported directly by tests and other modules.
# They point to the active game config so they work identically to before
# while being driven by config data instead of hardcoded literals.
MECHANIC_TERM_MAP       = _CONFIG.mechanic_term_map
MECHANIC_HINT_OVERRIDES = _CONFIG.mechanic_hint_overrides
GENERIC_TRIGGERS        = _CONFIG.generic_triggers
SYSTEM_PROMPT           = _CONFIG.system_prompt

# Stat abbreviations that BGE-small doesn't reliably bridge to the full word.
# Applied to the semantic query only (not keyword/mechanic extraction) so that
# "INT" → "Intelligence" improves embedding similarity without affecting filename matching.
_STAT_ABBREVS: list = _CONFIG.stat_abbrevs


def _expand_stat_abbrevs(text: str, config=None) -> str:
    """Expand uppercase stat abbreviations for better semantic embedding quality."""
    abbrevs = config.stat_abbrevs if config is not None else _STAT_ABBREVS
    for pattern, replacement in abbrevs:
        text = re.sub(pattern, replacement, text)
    return text


def _check_index_freshness(config=None) -> None:
    """
    Warn at startup if any knowledge_base .md files were modified after the
    ChromaDB index was last built.

    Edits to .md files are immediately visible via PATH B (raw file reads in
    _mechanic_search / _find_keyword_files) but are NOT reflected in PATH A
    (semantic/vector search) until the index is rebuilt.  This function makes
    that inconsistency visible rather than silent.

    Run `python scripts/rebuild_index.py --changed` to sync only changed files,
    or `python scripts/rebuild_index.py` for a full rebuild.
    """
    cfg = config if config is not None else DS2_CONFIG
    kb_dir = cfg.knowledge_base_dir
    # Per-game timestamp file; fall back to legacy single-game file.
    ts_file = os.path.join(DB_DIR, f".index_built_at_{cfg.game_id}")
    if not os.path.exists(ts_file):
        ts_file = INDEX_TIMESTAMP_FILE
    if not os.path.exists(ts_file):
        return  # index was built before timestamp tracking was added

    try:
        index_built_at = float(open(ts_file).read().strip())
    except (ValueError, OSError):
        return

    stale: list = []
    for fname in os.listdir(kb_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(kb_dir, fname)
        if os.path.getmtime(fpath) > index_built_at:
            stale.append(fname)

    if stale:
        print(
            f"\n[WARNING] INDEX STALE: {len(stale)} {cfg.game_id} knowledge_base file(s) modified "
            f"after the ChromaDB index was last built."
        )
        print(
            "  PATH B (keyword/mechanic raw reads) already sees these changes.\n"
            "  PATH A (semantic search) does NOT — rebuild to sync:\n"
            "    python scripts/rebuild_index.py --changed"
        )
        shown = stale[:5]
        for f in shown:
            print(f"    - {f}")
        if len(stale) > 5:
            print(f"    ... and {len(stale) - 5} more.")
        print()


def _db_has_embeddings() -> bool:
    """Check if the local db has a populated embeddings table — without opening ChromaDB."""
    import sqlite3 as _sq
    sqlite_path = os.path.join(DB_DIR, "chroma.sqlite3")
    if not os.path.exists(sqlite_path):
        return False
    try:
        conn = _sq.connect(sqlite_path)
        count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def _restore_baked_index():
    """Copy the pre-built index from db_baked/ into db/. Much faster than rebuilding."""
    if not os.path.isdir(DB_BAKED_DIR):
        return False
    print("Restoring pre-built index from db_baked/ (this takes seconds, not hours)...")
    shutil.rmtree(DB_DIR, ignore_errors=True)
    os.makedirs(DB_DIR, exist_ok=True)
    shutil.copytree(DB_BAKED_DIR, DB_DIR, dirs_exist_ok=True)
    print("Index restored from db_baked/")
    return True


def get_index(config=None):
    """Load existing index from ChromaDB or build it from the game's knowledge base."""
    cfg = config if config is not None else DS2_CONFIG
    collection_name = f"{cfg.game_id}_scholar"
    ts_file = os.path.join(DB_DIR, f".index_built_at_{cfg.game_id}")

    # Check db health via raw sqlite BEFORE opening ChromaDB (avoids WAL contamination).
    if not _db_has_embeddings():
        print("DB missing or empty — restoring from db_baked/ before opening ChromaDB...")
        if not _restore_baked_index():
            print("No db_baked/ found — will build from scratch.")

    def _open_collection():
        client = chromadb.PersistentClient(path=DB_DIR)
        return client, client.get_or_create_collection(collection_name)

    try:
        chroma_client, chroma_collection = _open_collection()
    except Exception as e:
        if "no such column" in str(e) or "OperationalError" in type(e).__name__:
            print(f"ChromaDB schema mismatch ({e}). Restoring from db_baked/...")
            if not _restore_baked_index():
                print("No db_baked/ found — falling back to full rebuild (may take a long time).")
            chroma_client, chroma_collection = _open_collection()
        else:
            raise
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # If the collection already has data, load it directly
    if chroma_collection.count() > 0:
        print(f"Loading existing index for {cfg.game_id} ({chroma_collection.count()} chunks)...")
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
            embed_model=EMBED_MODEL
        )
        _check_index_freshness(cfg)
    else:
        # Restore and reload — this path only hit if baked was unavailable above
        if _restore_baked_index():
            chroma_client, chroma_collection = _open_collection()
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context,
                embed_model=EMBED_MODEL
            )
        else:
            print(f"Building index for {cfg.game_id} from knowledge base... this may take a long time.")
            documents = SimpleDirectoryReader(cfg.knowledge_base_dir).load_data()
            print(f"Loaded {len(documents)} documents.")
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                embed_model=EMBED_MODEL,
                show_progress=True
            )
            print(f"Index built and saved to db/ ({cfg.game_id})")
            with open(ts_file, "w") as f:
                f.write(str(time.time()))

    return index


def extract_key_terms(query: str, config=None) -> list:
    """
    Extract key noun phrases and potential item/location/NPC names from a query.

    Looks for runs of Title-Case words (e.g. "Bastille Key", "Lost Bastille",
    "Mild Mannered Pate") and filters out common question/article words.
    Multi-word phrases are returned first since they're more specific.

    Returns a list of term strings, multi-word phrases before single words.
    """
    cfg = config if config is not None else DS2_CONFIG
    stop_caps = {
        "Where", "What", "How", "Who", "When", "Why", "Is", "Are", "Can",
        "Do", "Does", "The", "A", "An", "I", "In", "On", "At", "To",
        "For", "Of", "And", "Or", "But", "Get", "Find", "Tell", "Give",
        "Me", "My", "You", "Your", "There", "This", "That",
        "If", "Up", "Down", "Help", "Need", "Want", "Know", "Use", "Used",
    } | cfg.stop_words_caps

    # Strip possessives before matching so "McDuff's" → "McDuff", "Ornifex's" → "Ornifex"
    query_clean = re.sub(r"'s\b", "", query)

    # Match Title-Case words, allowing compositional connectors (of, the, to, and) between them.
    # e.g. "Ring of Binding", "Crown of the Sunken King", "Key to King's Passage"
    # NOTE: "in", "at", "for", "or" are intentionally excluded — they are sentence
    # prepositions, not part of DS2 item/NPC names. Including them causes "Gavlan in
    # Huntsman Copse" to collapse into one phrase that fuzzy-matches nothing.
    phrases = re.findall(
        r"\b[A-Z][a-z]+(?:\s+(?:(?:of|the|a|an|to|and)\s+)*[A-Z][a-z]+)*\b",
        query_clean,
    )

    multi_word = []
    single_word = []
    seen: set = set()

    for phrase in phrases:
        if phrase in seen:
            continue
        seen.add(phrase)
        words = phrase.split()
        if len(words) >= 2:
            multi_word.append(phrase)
        elif phrase not in stop_caps:
            single_word.append(phrase)

    # Fallback: catch CamelCase/mixed-case proper nouns the strict regex misses,
    # e.g. "McDuff" (M+c+D…), "NPC", "SotFS". Uses [A-Z]\w+ on the cleaned query.
    for word in re.findall(r"\b[A-Z]\w+\b", query_clean):
        if word not in seen and word not in stop_caps and len(word) >= 4:
            if not any(word in phrase for phrase in multi_word):
                seen.add(word)
                single_word.append(word)

    # Lowercase fallback: activates when no Title-Case terms were found (e.g. all-lowercase
    # query like "where is mcduff's workshop key"). Extracts significant words/bigrams so
    # _find_keyword_files can still do case-insensitive fuzzy filename matching.
    if not multi_word and not single_word:
        lc_stops = {
            "where", "what", "how", "who", "when", "why", "is", "are", "can",
            "do", "does", "the", "a", "an", "i", "in", "on", "at", "to",
            "for", "of", "and", "or", "but", "get", "find", "tell", "give",
            "me", "my", "you", "your", "there", "this", "that",
            "if", "up", "down", "help", "need", "want", "know", "use", "used",
        } | {w.lower() for w in cfg.stop_words_caps}
        clean = re.sub(r"[^a-z0-9\s]", "", query_clean.lower())
        lc_words = [w for w in clean.split() if w not in lc_stops and len(w) >= 4]
        # Bigrams first (more specific), then singles
        for i in range(len(lc_words) - 1):
            phrase = lc_words[i] + " " + lc_words[i + 1]
            if phrase not in seen:
                seen.add(phrase)
                multi_word.append(phrase)
        for w in lc_words:
            if w not in seen:
                seen.add(w)
                single_word.append(w)

    # Multi-word first (higher specificity), then single-word capitals
    return multi_word + single_word

def _read_file_section(fpath: str, hint_words: list, max_chars: int = FILE_READ_MAX_CHARS) -> str:
    """
    Read up to max_chars from a wiki file, starting from the section most
    relevant to hint_words rather than always from the top of the file.

    Algorithm:
    1. Read the whole file. If it fits within max_chars, return it whole.
    2. Otherwise, score every markdown heading (# / ## / ### / ####) by how
       many hint_words appear in the heading text. Start extraction from the
       highest-scoring heading (falls back to position 0 if no heading matches).
    3. Take content[start : start + max_chars].  Then cut cleanly at the last
       section heading that falls in the second half of that window — so the
       served chunk always ends at a natural section boundary rather than mid-
       sentence.

    This prevents the 3 000-char limit from serving only button-control tables
    for a query about Poise when the Poise section sits at char 12 000 of
    Combat.md, for example.
    """
    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if len(content) <= max_chars:
        return content

    hint_set = {w.lower() for w in hint_words if len(w) > 2}
    heading_re = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)
    headings = list(heading_re.finditer(content))

    # Find the heading whose text best matches hint_words
    start = 0
    if hint_set:
        best_score = 0
        for m in headings:
            score = sum(1 for w in hint_set if w in m.group(1).lower())
            if score > best_score:
                best_score = score
                start = m.start()

    chunk = content[start: start + max_chars]

    # Trim to the last section heading that falls past the midpoint of the chunk
    # so we don't serve a half-finished section at the tail.
    if len(chunk) == max_chars:
        midpoint = max_chars // 2
        last_heading_pos = None
        for m in re.finditer(r"^#{1,4}\s+", chunk, re.MULTILINE):
            if m.start() > midpoint:
                last_heading_pos = m.start()
        if last_heading_pos:
            chunk = chunk[:last_heading_pos]

    return chunk


def _mechanic_search(query: str, config=None, suppress_generic: bool = False) -> list:
    """
    Check the query against the game's MECHANIC_TERM_MAP using word-boundary matching.
    Returns (content, metadata, score) tuples for ALL matched pages.
    Score is 0.9 for all mechanic map hits.

    Note: deliberately does NOT filter against already-seen files so that
    retrieve_context can always apply the score boost even for pages the
    semantic search already found (previously a bug where low-scoring
    semantic hits blocked the mechanic boost entirely).

    Uses _read_file_section with the matched trigger words as hints so that
    long mechanic pages (e.g. Combat.md at 35 k chars) start extraction at
    the relevant heading rather than always from the top of the file.
    """
    cfg = config if config is not None else DS2_CONFIG
    term_map       = cfg.mechanic_term_map
    hint_overrides = cfg.mechanic_hint_overrides
    gen_triggers   = cfg.generic_triggers
    kb_dir         = cfg.knowledge_base_dir

    query_lower = query.lower()
    files_to_add: list = []
    added_fnames: set = set()

    for trigger, fnames in term_map.items():
        # Word-boundary check: trigger must appear as whole word(s) in query.
        # Allow optional trailing 's' so "mcduffs" matches "mcduff",
        # "gavlans" matches "gavlan", etc. (handles possessives without apostrophe).
        pattern = r"\b" + re.escape(trigger) + r"s?\b"
        if re.search(pattern, query_lower):
            if suppress_generic and trigger in gen_triggers:
                continue
            for fname in fnames:
                if fname not in added_fnames and os.path.exists(
                    os.path.join(kb_dir, fname)
                ):
                    added_fnames.add(fname)
                    # Store trigger alongside path so we can use it as a hint
                    # for section-aware extraction in long files.
                    files_to_add.append((os.path.join(kb_dir, fname), fname, trigger))

    results = []
    for fpath, fname, trigger in files_to_add:
        # Use per-trigger hint overrides when the trigger word itself won't match
        # any heading in the target file (e.g. "cheese" → use "strategy"/"tips").
        hint_words = hint_overrides.get(trigger, trigger.split())
        content = _read_file_section(fpath, hint_words)
        results.append((content, {"file_name": fname}, 0.9))
    return results


def _find_keyword_files(terms: list, config=None) -> list:
    """
    Search game knowledge_base filenames for matches to extracted terms.

    For each term:
      1. Try an exact filename match: "Bastille Key" → "Bastille_Key.md"
      2. Fall back to fuzzy: any filename whose normalized form contains all
         words of the term (e.g. catches "The_Lost_Bastille.md" for "Lost Bastille")
         Capped at MAX_FUZZY_PER_TERM results per term to prevent generic single
         words (e.g. "weapon", "ring") from flooding the scored dict.

    Returns a list of (content, metadata_dict, score) tuples.
    Exact matches score 1.0, fuzzy matches score 0.5.
    File content is extracted via _read_file_section (section-aware, up to
    FILE_READ_MAX_CHARS chars) so that long area/mechanic pages don't serve
    only a header block when the relevant content is deeper in the file.
    """
    cfg = config if config is not None else DS2_CONFIG
    kb_dir = cfg.knowledge_base_dir

    MAX_FUZZY_PER_TERM = 5
    results = []
    seen_paths: set = set()
    filenames = _get_kb_filenames(cfg)

    for term in terms:
        hint_words = term.split()

        # --- Exact filename match ---
        candidate = term.replace(" ", "_") + ".md"
        exact_path = os.path.join(kb_dir, candidate)
        if os.path.exists(exact_path) and exact_path not in seen_paths:
            seen_paths.add(exact_path)
            content = _read_file_section(exact_path, hint_words)
            results.append((content, {"file_name": candidate}, 1.0))
            continue  # exact hit — no need to fuzzy-search for this term

        # --- Fuzzy filename match ---
        # Normalize term: lowercase, strip apostrophes/hyphens for comparison
        term_words = re.sub(r"['\-]", " ", term.lower()).split()

        fuzzy_count = 0
        for fname in filenames:
            if fuzzy_count >= MAX_FUZZY_PER_TERM:
                break
            fpath = os.path.join(kb_dir, fname)
            if fpath in seen_paths:
                continue
            # Normalize filename: underscores/hyphens → spaces, drop .md,
            # collapse URL-encoded sequences (e.g. _27_ for apostrophes)
            fname_norm = fname[:-3].lower()                          # strip .md
            fname_norm = re.sub(r"_[0-9a-f]{2}_?", " ", fname_norm)  # _XX_ → space
            fname_norm = fname_norm.replace("_", " ").replace("-", " ")

            # Also accept a word without its trailing 's' to handle possessives
            # typed without an apostrophe: "Mans" → try "Man" against "man s wharf".
            if all(w in fname_norm or (w.endswith("s") and len(w) > 2 and w[:-1] in fname_norm)
                   for w in term_words):
                seen_paths.add(fpath)
                content = _read_file_section(fpath, hint_words)
                results.append((content, {"file_name": fname}, 0.5))
                fuzzy_count += 1

    return results


def _build_fname_lookup(config=None) -> dict:
    """
    Build a dict mapping every normalized KB filename to its actual filename.

    Normalization strips .md, lowercases, expands URL-encoded sequences
    (_27_ → space), and converts underscores/hyphens to spaces.
    e.g. "Titanite_Shard.md" → "titanite shard"
         "Crown_of_the_Sunken_King.md" → "crown of the sunken king"
         "Black_Witch_27s_Staff.md" → "black witch s staff"

    Used by _auto_filename_search to match n-grams from the user's query directly
    against page names — no manual MECHANIC_TERM_MAP entry needed for straightforward
    item/area names.
    """
    lookup: dict = {}
    for fname in _get_kb_filenames(config):
        norm = fname[:-3].lower()
        norm = re.sub(r"_[0-9a-f]{2}_?", " ", norm)   # URL-encoded chars → space
        norm = re.sub(r"[_\-]", " ", norm)             # underscores/hyphens → space
        norm = re.sub(r"\s+", " ", norm).strip()
        if norm:
            lookup[norm] = fname
    return lookup


def _auto_filename_search(query: str, config=None) -> list:
    """
    Extract 4→3→2-word n-grams from the lowercase query and match them against
    the normalized KB filename lookup (_FNAME_LOOKUP) for the given game.

    Longer n-grams are tried first (more specific); once a span is consumed it is
    not reused for shorter grams, preventing over-matching.

    Returns (content, metadata, score) tuples. Score 0.7 — higher than fuzzy
    keyword match (0.5) but below the manual mechanic map (0.9).

    This supplements the mechanic map for item/area names that map directly to a
    wiki page without needing a conceptual bridge (e.g. "bone staff" → Bone_Staff.md,
    "iron keep" → Iron_Keep.md). It does NOT replace entries like "die"→Hollowing.md
    where there is no filename correspondence.
    """
    cfg = config if config is not None else DS2_CONFIG
    gid = cfg.game_id
    if gid not in _FNAME_LOOKUP:
        _FNAME_LOOKUP[gid] = _build_fname_lookup(cfg)
    lookup = _FNAME_LOOKUP[gid]
    kb_dir = cfg.knowledge_base_dir

    q_clean = re.sub(r"[^a-z0-9\s]", " ", query.lower())
    words = q_clean.split()

    results = []
    seen_fnames: set = set()
    used_positions: set = set()  # word indices already consumed by a longer n-gram

    for n in (4, 3, 2):
        for i in range(len(words) - n + 1):
            # Skip if any position in this span was already used by a longer gram
            span = set(range(i, i + n))
            if span & used_positions:
                continue
            gram = " ".join(words[i:i + n])
            if gram in lookup:
                fname = lookup[gram]
                if fname not in seen_fnames:
                    seen_fnames.add(fname)
                    used_positions |= span
                    fpath = os.path.join(kb_dir, fname)
                    content = _read_file_section(fpath, gram.split())
                    results.append((content, {"file_name": fname}, 0.7))

    return results


def retrieve_context(index, query: str, config=None, top_k: int = 7, raw_query: str = None, brief_stats: str = "") -> str:
    """
    Retrieve the most relevant wiki chunks for a query using hybrid search.

    Parameters:
      query       — full question string (may include player stats preamble) used for
                    semantic/vector search so the embedding benefits from player context.
      raw_query   — the user's original question WITHOUT any stats preamble, used for
                    keyword/term extraction and mechanic-term matching so that stat labels
                    like "Soul Level" or "Current Area" don't crowd the keyword results.
                    Falls back to `query` if not provided.
      brief_stats — compact player summary (e.g. "STR build, SL62, Greatsword +2") passed
                    to the Haiku query rewriter so it can output build-relevant keywords.

    Steps:
      1. Semantic search + Haiku query rewrite run in parallel (independent operations).
      2. Keyword/filename search using the rewritten term_query.
      3. Mechanic term map — injects pages for lowercase mechanics the embedding
         model can't bridge (die→Hollowing, hollow→Human_Effigy, covenant→Covenants, …).
      4. Merge all results keyed by filename, boosting pages found by multiple methods.
      5. Return the top `top_k` (default 10) chunks formatted as context.
    """
    cfg = config if config is not None else DS2_CONFIG
    gid = cfg.game_id

    # Use raw_query for term extraction so player-stats labels don't pollute results
    term_query = raw_query if raw_query is not None else query

    # Cache check — identical queries (same raw text, top_k, player summary) skip
    # the full hybrid search pipeline and return the previously computed context.
    cache_key = (term_query, top_k, brief_stats)
    game_cache = _RETRIEVE_CACHE.setdefault(gid, {})
    if cache_key in game_cache:
        print("[TIMING] retrieve_context cache hit — skipping pipeline")
        return game_cache[cache_key]

    # 1. Semantic search and Haiku query rewrite run concurrently — they're independent.
    #    Semantic uses the full augmented query; rewrite enriches term_query for keyword
    #    and mechanic search. Running in parallel hides the ~300ms Haiku API latency
    #    behind the ChromaDB HNSW search, cutting pre-stream latency roughly in half.
    # Use the raw question (without player-stats preamble) for the semantic embedding.
    # Including "Current Area: Lost Bastille" in the embedding vector biases results toward
    # area files even for unrelated questions ("where can I buy titanite shards?").
    # The full preamble is still sent to Claude for generation — it just shouldn't
    # distort which wiki pages get retrieved.
    semantic_query = _expand_stat_abbrevs(term_query, cfg)

    t0 = time.time()
    retriever = index.as_retriever(similarity_top_k=50)
    with ThreadPoolExecutor(max_workers=2) as executor:
        semantic_future = executor.submit(retriever.retrieve, semantic_query)
        rewrite_future = executor.submit(rewrite_query_for_retrieval, term_query, cfg.game_id, brief_stats)
        semantic_nodes = semantic_future.result()
        t_semantic = time.time()
        term_query = rewrite_future.result()
        t_rewrite = time.time()
    print(f"[TIMING] semantic={t_semantic-t0:.2f}s  rewrite={t_rewrite-t0:.2f}s  parallel_wall={t_rewrite-t0:.2f}s")

    # Deduplicate by NORMALIZED filename so URL-encoded and plain variants of the
    # same file (e.g. "No_Man_27s_Wharf.md" and "No_Man_s_Wharf.md") collapse into
    # one slot instead of burning multiple top_k positions on identical content.
    scored: dict = {}  # norm_fname -> (text, metadata, score)
    for node in semantic_nodes:
        fname = node.metadata.get("file_name", "unknown")
        nkey = _norm_fname(fname)
        node_score = node.score or 0.0
        if nkey not in scored or node_score > scored[nkey][2]:
            scored[nkey] = (node.text, node.metadata, node_score)

    # 2. Keyword/filename search (proper nouns — capitalized terms in raw question only)
    t_kw0 = time.time()
    terms = extract_key_terms(term_query, cfg)
    if terms:
        for content, metadata, kw_score in _find_keyword_files(terms, cfg):
            fname = metadata.get("file_name", "unknown")
            nkey = _norm_fname(fname)
            if nkey in scored:
                _prev_text, prev_meta, prev_score = scored[nkey]
                # Prefer keyword content (top of file) over whatever chunk semantic
                # search happened to return — avoids empty/irrelevant chunks winning.
                scored[nkey] = (content, prev_meta, prev_score + kw_score)
            else:
                scored[nkey] = (content, metadata, kw_score)

    # 3. Mechanic term map (lowercase mechanics the embedding model can't bridge).
    #    If a specific named entity was already found via keyword search (terms is non-empty),
    #    suppress generic aggregation triggers (cheese, easy boss) so their broad page lists
    #    don't crowd out the specific boss/NPC page the user is actually asking about.
    for content, metadata, mech_score in _mechanic_search(term_query, cfg, suppress_generic=bool(terms)):
        fname = metadata.get("file_name", "unknown")
        nkey = _norm_fname(fname)
        if nkey in scored:
            _prev_text, prev_meta, prev_score = scored[nkey]
            scored[nkey] = (content, prev_meta, prev_score + mech_score)
        else:
            scored[nkey] = (content, metadata, mech_score)

    # 3b. Auto n-gram filename search — catches item/area names that map directly to a
    #     wiki page without a manual MECHANIC_TERM_MAP entry (score 0.7).
    for content, metadata, auto_score in _auto_filename_search(term_query, cfg):
        fname = metadata.get("file_name", "unknown")
        nkey = _norm_fname(fname)
        if nkey in scored:
            _prev_text, prev_meta, prev_score = scored[nkey]
            scored[nkey] = (content, prev_meta, prev_score + auto_score)
        else:
            scored[nkey] = (content, metadata, auto_score)
    print(f"[TIMING] keyword+mechanic+auto={time.time()-t_kw0:.2f}s")

    # 4. Sort by combined score descending, keep top_k
    sorted_results = sorted(scored.values(), key=lambda x: x[2], reverse=True)[:top_k]

    context_parts = []
    for text, metadata, _score in sorted_results:
        source = metadata.get("file_name", "unknown")
        context_parts.append(f"--- Source: {source} ---\n{text}")

    result = "\n\n".join(context_parts)

    # Store in per-game cache with FIFO eviction
    if len(game_cache) >= _RETRIEVE_CACHE_MAX:
        game_cache.pop(next(iter(game_cache)))
    game_cache[cache_key] = result
    return result


def ask(index, question: str, config=None, chat_history: list = None, raw_question: str = None, brief_stats: str = "") -> str:
    """
    Ask a question using RAG + Claude.
    chat_history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    raw_question is the user's original question without any player stats preamble;
    it is used for keyword/term extraction so stat labels don't pollute results.
    brief_stats is a compact player summary passed to the Haiku query rewriter.
    """
    cfg = config if config is not None else DS2_CONFIG
    context = retrieve_context(index, question, config=cfg, raw_query=raw_question, brief_stats=brief_stats)

    messages = []
    if chat_history:
        messages.extend(chat_history)
    messages.append({
        "role": "user",
        "content": f"Wiki Context:\n{context}\n\nQuestion: {question}",
    })

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=[{"type": "text", "text": cfg.system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )

    return response.content[0].text


def stream_ask(index, question: str, config=None, chat_history: list = None, raw_question: str = None, brief_stats: str = ""):
    """
    Ask a question using RAG + Claude, streaming the response.
    Yields text chunks as they arrive from the API.
    raw_question is the user's original question without any player stats preamble.
    brief_stats is a compact player summary passed to the Haiku query rewriter.
    """
    cfg = config if config is not None else DS2_CONFIG
    t_start = time.time()
    context = retrieve_context(index, question, config=cfg, raw_query=raw_question, brief_stats=brief_stats)
    t_retrieved = time.time()
    print(f"[TIMING] retrieve_context total={t_retrieved-t_start:.2f}s")

    messages = []
    if chat_history:
        messages.extend(chat_history)
    messages.append({
        "role": "user",
        "content": f"Wiki Context:\n{context}\n\nQuestion: {question}",
    })

    with claude.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=[{"type": "text", "text": cfg.system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    ) as stream:
        first_token = True
        for text in stream.text_stream:
            if first_token:
                print(f"[TIMING] time_to_first_token={time.time()-t_retrieved:.2f}s  total_pre_stream={time.time()-t_start:.2f}s")
                first_token = False
            yield text


# Initialize indexes for all configured games at module load time
_INDEXES: dict = {}
for _gid, _gcfg in _ALL_CONFIGS.items():
    print(f"Initializing {_gcfg.bot_name} RAG pipeline ({_gid})...")
    _INDEXES[_gid] = get_index(_gcfg)
index = _INDEXES["ds2"]  # backwards-compat export
print("Ready.\n")
