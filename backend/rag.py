# RAG (Retrieval-Augmented Generation) pipeline for DS2 Scholar.
# Handles loading the knowledge base into ChromaDB, embedding queries,
# retrieving relevant documents, and generating answers via the Anthropic API.

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

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
DB_DIR = os.path.join(BASE_DIR, "db")
DB_BAKED_DIR = os.path.join(BASE_DIR, "db_baked")  # pre-built index baked into Docker image

# Anthropic client
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


@lru_cache(maxsize=256)
def rewrite_query_for_retrieval(question: str, brief_stats: str = "") -> str:
    """
    Use Claude Haiku to convert a user question into DS2 retrieval keywords.

    The output is appended to the original question so the existing heuristics
    (extract_key_terms, mechanic map) still fire on the original phrasing, while
    the rewritten keywords improve recall for vague or lowercase queries.

    brief_stats: compact player summary, e.g. "STR build, SL62, Greatsword +2, Lost Bastille"
    Falls back to the original question if the Haiku call fails.
    """
    stats_note = f"\nPlayer: {brief_stats}" if brief_stats else ""
    try:
        response = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": (
                    f"Convert this Dark Souls 2 question into wiki search keywords. "
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

# Cached list of all .md filenames in the knowledge base (populated on first use)
_KB_FILENAMES = None

# Module-level retrieval cache — avoids re-running the full hybrid search for
# identical queries (e.g. user submits the same question twice, or chat history
# causes the same raw_query to be processed multiple times in a session).
# Key: (term_query, top_k, brief_stats). FIFO eviction at 256 entries.
_RETRIEVE_CACHE: dict = {}
_RETRIEVE_CACHE_MAX = 256

# Auto n-gram filename lookup — populated lazily on first use (needs KB dir ready).
# Maps normalized filenames (lowercase, underscores→spaces) to actual filenames.
_FNAME_LOOKUP = None  # dict or None; populated lazily on first use


def _norm_fname(fname: str) -> str:
    """
    Normalize a filename for deduplication.
    Collapses URL-encoding (_27_ → _) and repeated underscores so both
    encoded and plain variants of the same file map to the same key.
    e.g. "No_Man_27s_Wharf.md" and "No_Man_s_Wharf.md" → same key.
    """
    n = re.sub(r"_[0-9a-f]{2}_?", "_", fname.lower())
    return re.sub(r"_+", "_", n)


def _get_kb_filenames() -> list:
    """
    Return a cached, deduplicated list of .md filenames in the knowledge base.

    The scraper saved many pages twice — once with URL-encoded apostrophes/commas
    (e.g. "McDuff_27s_Workshop.md", "Aava_2C_the_King_27s_Pet.md") and once with
    plain separators ("McDuff_s_Workshop.md", "Aava_the_King_s_Pet.md").
    We keep the alphabetically-later (plain) version and discard the _XX_ variant
    so duplicate content doesn't waste top_k context slots.
    """
    global _KB_FILENAMES
    if _KB_FILENAMES is None:
        all_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith(".md")]
        seen: dict = {}  # norm_key → fname; later (alphabetically) wins
        for fname in sorted(all_files):
            seen[_norm_fname(fname)] = fname  # plain _s_ sorts after _27s_, so it wins
        _KB_FILENAMES = list(seen.values())
    return _KB_FILENAMES


# DS2 stat abbreviations that BGE-small doesn't reliably bridge to the full word.
# Applied to the semantic query only (not keyword/mechanic extraction) so that
# "INT" → "Intelligence" improves embedding similarity without affecting filename matching.
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


def _expand_stat_abbrevs(text: str) -> str:
    """Expand uppercase DS2 stat abbreviations for better semantic embedding quality."""
    for pattern, replacement in _STAT_ABBREVS:
        text = re.sub(pattern, replacement, text)
    return text


def _check_index_freshness() -> None:
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
    if not os.path.exists(INDEX_TIMESTAMP_FILE):
        return  # index was built before timestamp tracking was added; can't determine age

    try:
        index_built_at = float(open(INDEX_TIMESTAMP_FILE).read().strip())
    except (ValueError, OSError):
        return

    stale: list = []
    for fname in os.listdir(KNOWLEDGE_BASE_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(KNOWLEDGE_BASE_DIR, fname)
        if os.path.getmtime(fpath) > index_built_at:
            stale.append(fname)

    if stale:
        print(
            f"\n[WARNING] INDEX STALE: {len(stale)} knowledge_base file(s) modified "
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


def get_index():
    """Load existing index from ChromaDB or build it from knowledge base."""
    # Check db health via raw sqlite BEFORE opening ChromaDB (avoids WAL contamination).
    if not _db_has_embeddings():
        print("DB missing or empty — restoring from db_baked/ before opening ChromaDB...")
        if not _restore_baked_index():
            print("No db_baked/ found — will build from scratch.")

    def _open_collection():
        client = chromadb.PersistentClient(path=DB_DIR)
        return client, client.get_or_create_collection("ds2_scholar")

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
        print(f"Loading existing index ({chroma_collection.count()} chunks)...")
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
            embed_model=EMBED_MODEL
        )
        _check_index_freshness()
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
            print("Building index from knowledge base... this may take a long time.")
            documents = SimpleDirectoryReader(KNOWLEDGE_BASE_DIR).load_data()
            print(f"Loaded {len(documents)} documents.")
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                embed_model=EMBED_MODEL,
                show_progress=True
            )
            print("Index built and saved to db/")
            with open(INDEX_TIMESTAMP_FILE, "w") as f:
                f.write(str(time.time()))

    return index


def extract_key_terms(query: str) -> list:
    """
    Extract key noun phrases and potential item/location/NPC names from a DS2 query.

    Looks for runs of Title-Case words (e.g. "Bastille Key", "Lost Bastille",
    "Mild Mannered Pate") and filters out common question/article words.
    Multi-word phrases are returned first since they're more specific.

    Returns a list of term strings, multi-word phrases before single words.
    """
    stop_caps = {
        "Where", "What", "How", "Who", "When", "Why", "Is", "Are", "Can",
        "Do", "Does", "The", "A", "An", "I", "In", "On", "At", "To",
        "For", "Of", "And", "Or", "But", "Get", "Find", "Tell", "Give",
        "Me", "My", "You", "Your", "There", "This", "That", "Dark", "Souls",
        "If", "Up", "Down", "Help", "Need", "Want", "Know", "Use", "Used",
    }

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
            "me", "my", "you", "your", "there", "this", "that", "dark", "souls",
            "if", "up", "down", "help", "need", "want", "know", "use", "used",
        }
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


# Maps lowercase query substrings to the mechanic pages the embedding model
# struggles to bridge. Checked with word-boundary matching at query time.
# Score 0.9 — confident manual mapping, slightly below exact filename match (1.0).
MECHANIC_TERM_MAP: dict = {
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
    "soul vessel":  ["Soul_Vessel.md"] if os.path.exists(os.path.join(KNOWLEDGE_BASE_DIR, "Soul_Vessel.md")) else ["Stats.md"],
    "respec":       ["Soul_Vessel.md"] if os.path.exists(os.path.join(KNOWLEDGE_BASE_DIR, "Soul_Vessel.md")) else ["Stats.md"],
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
    "pharros":      ["Pharros_Lockstone.md"],
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
    "sunken king":     ["Crown_of_the_Sunken_King.md"] if os.path.exists(os.path.join(KNOWLEDGE_BASE_DIR, "Crown_of_the_Sunken_King.md")) else [],
    "ivory king":      ["Crown_of_the_Ivory_King.md"] if os.path.exists(os.path.join(KNOWLEDGE_BASE_DIR, "Crown_of_the_Ivory_King.md")) else [],
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
    "aldia":               ["Aldia_s_Keep.md", "Aldia_Scholar_of_the_First_Sin.md"],
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
    "aldia":               ["Aldia_Scholar_of_the_First_Sin.md"],
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


# Per-trigger hint-word overrides for _mechanic_search.
# When a trigger's own words are useless for heading-matching (e.g. "cheese" → no boss
# page has a heading called "Cheese"), supply better hint words so _read_file_section
# starts extraction at the relevant section (Strategy, Tips, Notes) rather than
# always from position 0 of the file.
MECHANIC_HINT_OVERRIDES: dict = {
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
}

# Triggers whose injected page lists are "aggregation" answers — useful for broad questions
# ("what bosses can be cheesed?") but add noise when the query also names a specific entity
# ("does the Smelter Demon have a cheese?"). When a proper noun is detected alongside one of
# these triggers, keyword + semantic search handles the specific entity instead, and the
# generic list is suppressed so unrelated pages don't flood the top_k slots.
GENERIC_TRIGGERS: set = {"cheese", "cheesed", "cheeseable", "cheesing", "easy boss"}


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


def _mechanic_search(query: str, suppress_generic: bool = False) -> list:
    """
    Check the query against MECHANIC_TERM_MAP using word-boundary matching.
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
    query_lower = query.lower()
    files_to_add: list = []
    added_fnames: set = set()

    for trigger, fnames in MECHANIC_TERM_MAP.items():
        # Word-boundary check: trigger must appear as whole word(s) in query.
        # Allow optional trailing 's' so "mcduffs" matches "mcduff",
        # "gavlans" matches "gavlan", etc. (handles possessives without apostrophe).
        pattern = r"\b" + re.escape(trigger) + r"s?\b"
        if re.search(pattern, query_lower):
            if suppress_generic and trigger in GENERIC_TRIGGERS:
                continue
            for fname in fnames:
                if fname not in added_fnames and os.path.exists(
                    os.path.join(KNOWLEDGE_BASE_DIR, fname)
                ):
                    added_fnames.add(fname)
                    # Store trigger alongside path so we can use it as a hint
                    # for section-aware extraction in long files.
                    files_to_add.append((os.path.join(KNOWLEDGE_BASE_DIR, fname), fname, trigger))

    results = []
    for fpath, fname, trigger in files_to_add:
        # Use per-trigger hint overrides when the trigger word itself won't match
        # any heading in the target file (e.g. "cheese" → use "strategy"/"tips").
        hint_words = MECHANIC_HINT_OVERRIDES.get(trigger, trigger.split())
        content = _read_file_section(fpath, hint_words)
        results.append((content, {"file_name": fname}, 0.9))
    return results


def _find_keyword_files(terms: list) -> list:
    """
    Search knowledge_base filenames for matches to extracted terms.

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
    MAX_FUZZY_PER_TERM = 5
    results = []
    seen_paths: set = set()
    filenames = _get_kb_filenames()

    for term in terms:
        hint_words = term.split()

        # --- Exact filename match ---
        candidate = term.replace(" ", "_") + ".md"
        exact_path = os.path.join(KNOWLEDGE_BASE_DIR, candidate)
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
            fpath = os.path.join(KNOWLEDGE_BASE_DIR, fname)
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


def _build_fname_lookup() -> dict:
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
    for fname in _get_kb_filenames():
        norm = fname[:-3].lower()
        norm = re.sub(r"_[0-9a-f]{2}_?", " ", norm)   # URL-encoded chars → space
        norm = re.sub(r"[_\-]", " ", norm)             # underscores/hyphens → space
        norm = re.sub(r"\s+", " ", norm).strip()
        if norm:
            lookup[norm] = fname
    return lookup


def _auto_filename_search(query: str) -> list:
    """
    Extract 4→3→2-word n-grams from the lowercase query and match them against
    the normalized KB filename lookup (_FNAME_LOOKUP).

    Longer n-grams are tried first (more specific); once a span is consumed it is
    not reused for shorter grams, preventing over-matching.

    Returns (content, metadata, score) tuples. Score 0.7 — higher than fuzzy
    keyword match (0.5) but below the manual mechanic map (0.9).

    This supplements the mechanic map for item/area names that map directly to a
    wiki page without needing a conceptual bridge (e.g. "bone staff" → Bone_Staff.md,
    "iron keep" → Iron_Keep.md). It does NOT replace entries like "die"→Hollowing.md
    where there is no filename correspondence.
    """
    global _FNAME_LOOKUP
    if _FNAME_LOOKUP is None:
        _FNAME_LOOKUP = _build_fname_lookup()

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
            if gram in _FNAME_LOOKUP:
                fname = _FNAME_LOOKUP[gram]
                if fname not in seen_fnames:
                    seen_fnames.add(fname)
                    used_positions |= span
                    fpath = os.path.join(KNOWLEDGE_BASE_DIR, fname)
                    content = _read_file_section(fpath, gram.split())
                    results.append((content, {"file_name": fname}, 0.7))

    return results


def retrieve_context(index, query: str, top_k: int = 7, raw_query: str = None, brief_stats: str = "") -> str:
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
    # Use raw_query for term extraction so player-stats labels don't pollute results
    term_query = raw_query if raw_query is not None else query

    # Cache check — identical queries (same raw text, top_k, player summary) skip
    # the full hybrid search pipeline and return the previously computed context.
    cache_key = (term_query, top_k, brief_stats)
    if cache_key in _RETRIEVE_CACHE:
        print("[TIMING] retrieve_context cache hit — skipping pipeline")
        return _RETRIEVE_CACHE[cache_key]

    # 1. Semantic search and Haiku query rewrite run concurrently — they're independent.
    #    Semantic uses the full augmented query; rewrite enriches term_query for keyword
    #    and mechanic search. Running in parallel hides the ~300ms Haiku API latency
    #    behind the ChromaDB HNSW search, cutting pre-stream latency roughly in half.
    # Use the raw question (without player-stats preamble) for the semantic embedding.
    # Including "Current Area: Lost Bastille" in the embedding vector biases results toward
    # area files even for unrelated questions ("where can I buy titanite shards?").
    # The full preamble is still sent to Claude for generation — it just shouldn't
    # distort which wiki pages get retrieved.
    semantic_query = _expand_stat_abbrevs(term_query)

    t0 = time.time()
    retriever = index.as_retriever(similarity_top_k=50)
    with ThreadPoolExecutor(max_workers=2) as executor:
        semantic_future = executor.submit(retriever.retrieve, semantic_query)
        rewrite_future = executor.submit(rewrite_query_for_retrieval, term_query, brief_stats)
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
    terms = extract_key_terms(term_query)
    if terms:
        for content, metadata, kw_score in _find_keyword_files(terms):
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
    for content, metadata, mech_score in _mechanic_search(term_query, suppress_generic=bool(terms)):
        fname = metadata.get("file_name", "unknown")
        nkey = _norm_fname(fname)
        if nkey in scored:
            _prev_text, prev_meta, prev_score = scored[nkey]
            scored[nkey] = (content, prev_meta, prev_score + mech_score)
        else:
            scored[nkey] = (content, metadata, mech_score)

    # 3b. Auto n-gram filename search — catches item/area names that map directly to a
    #     wiki page without a manual MECHANIC_TERM_MAP entry (score 0.7).
    for content, metadata, auto_score in _auto_filename_search(term_query):
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

    # Store in cache with FIFO eviction
    if len(_RETRIEVE_CACHE) >= _RETRIEVE_CACHE_MAX:
        _RETRIEVE_CACHE.pop(next(iter(_RETRIEVE_CACHE)))
    _RETRIEVE_CACHE[cache_key] = result
    return result


SYSTEM_PROMPT = """You are Scholar, a Dark Souls 2 companion AI grounded strictly in the Fextralife wiki context provided below.

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


def ask(index, question: str, chat_history: list = None, raw_question: str = None, brief_stats: str = "") -> str:
    """
    Ask a question using RAG + Claude.
    chat_history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    raw_question is the user's original question without any player stats preamble;
    it is used for keyword/term extraction so stat labels don't pollute results.
    brief_stats is a compact player summary passed to the Haiku query rewriter.
    """
    context = retrieve_context(index, question, raw_query=raw_question, brief_stats=brief_stats)

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
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    return response.content[0].text


def stream_ask(index, question: str, chat_history: list = None, raw_question: str = None, brief_stats: str = ""):
    """
    Ask a question using RAG + Claude, streaming the response.
    Yields text chunks as they arrive from the API.
    raw_question is the user's original question without any player stats preamble.
    brief_stats is a compact player summary passed to the Haiku query rewriter.
    """
    t_start = time.time()
    context = retrieve_context(index, question, raw_query=raw_question, brief_stats=brief_stats)
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
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        first_token = True
        for text in stream.text_stream:
            if first_token:
                print(f"[TIMING] time_to_first_token={time.time()-t_retrieved:.2f}s  total_pre_stream={time.time()-t_start:.2f}s")
                first_token = False
            yield text


# Initialize index at module load time
print("Initializing DS2 Scholar RAG pipeline...")
index = get_index()
print("Ready.\n")
