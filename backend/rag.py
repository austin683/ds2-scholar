# RAG (Retrieval-Augmented Generation) pipeline for DS2 Scholar.
# Handles loading the knowledge base into ChromaDB, embedding queries,
# retrieving relevant documents, and generating answers via the Anthropic API.

import os
import re
import time
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import chromadb
import anthropic

load_dotenv()

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
DB_DIR = os.path.join(BASE_DIR, "db")

# Anthropic client
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
FILE_READ_MAX_CHARS = 8000

# Timestamp file written when the index is freshly built; used for stale detection.
INDEX_TIMESTAMP_FILE = os.path.join(DB_DIR, ".index_built_at")

# Use a free local embedding model — no OpenAI needed
EMBED_MODEL = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Cached list of all .md filenames in the knowledge base (populated on first use)
_KB_FILENAMES = None


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


def get_index():
    """Load existing index from ChromaDB or build it from knowledge base."""
    chroma_client = chromadb.PersistentClient(path=DB_DIR)
    chroma_collection = chroma_client.get_or_create_collection("ds2_scholar")
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
        # Build index from scratch
        print("Building index from knowledge base... this may take a few minutes.")
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
        # Record build timestamp so future startups can detect stale files.
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
    "attunement slots": ["Attunement.md"],
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
    "infusion":     ["Infusion.md"] if os.path.exists(os.path.join(KNOWLEDGE_BASE_DIR, "Infusion.md")) else ["Combat.md"],
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
    # Spell schools — embedding model can't bridge short query words to correct pages
    "hex":          ["Hexes.md"],
    "hexes":        ["Hexes.md"],
    "dark magic":   ["Hexes.md"],
    "dark spell":   ["Hexes.md"],
    "dark spells":  ["Hexes.md"],
    "sorcery trainer":  ["Carhillion_of_the_Fold.md"],
    "sorcery":          ["Sorceries.md"],
    "sorceries":        ["Sorceries.md"],
    "hex trainer":      ["Felkin_the_Outcast.md"],
    "miracle trainer":  ["Licia_of_Lindeldt.md"],
    "miracle":          ["Miracles.md"],
    "miracles":         ["Miracles.md"],
    "pyromancy trainer": ["Rosabeth_of_Melfia.md"],
    "pyromancy":        ["Pyromancies.md"],
    "pyromancies":      ["Pyromancies.md"],
    # Weapon upgrade / crafting
    "upgrade":      ["Upgrades.md"],
    "upgrades":     ["Upgrades.md"],
    "reinforce":    ["Upgrades.md"],
    "titanite":     ["Upgrades.md"],
    "dull ember":   ["Dull_Ember.md", "Steady_Hand_McDuff.md"],
    "ember":        ["Dull_Ember.md"],
    # Exploration / items
    "torch":        ["Torch.md"],
    "pharros":      ["Pharros_Lockstone.md"],
    "agape":        ["Agape_Ring.md"],
    "fragrant branch": ["Fragrant_Branch_of_Yore.md"],
    "branch of yore":  ["Fragrant_Branch_of_Yore.md"],
    "unpetrify":       ["Fragrant_Branch_of_Yore.md"],
    # DLC areas — embedding model fails to bridge short area names to DLC pages
    "brume tower":     ["Brume_Tower.md", "Crown_of_the_Old_Iron_King.md"],
    "sunken king":     ["Crown_of_the_Sunken_King.md"] if os.path.exists(os.path.join(KNOWLEDGE_BASE_DIR, "Crown_of_the_Sunken_King.md")) else [],
    "ivory king":      ["Crown_of_the_Ivory_King.md"] if os.path.exists(os.path.join(KNOWLEDGE_BASE_DIR, "Crown_of_the_Ivory_King.md")) else [],
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
    "gavlan":              ["Gavlan.md", "Lonesome_Gavlan.md"],
    "lonesome gavlan":     ["Gavlan.md"],
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


def retrieve_context(index, query: str, top_k: int = 10, raw_query: str = None) -> str:
    """
    Retrieve the most relevant wiki chunks for a query using hybrid search.

    Parameters:
      query     — full question string (may include player stats preamble) used for
                  semantic/vector search so the embedding benefits from player context.
      raw_query — the user's original question WITHOUT any stats preamble, used for
                  keyword/term extraction and mechanic-term matching so that stat labels
                  like "Soul Level" or "Current Area" don't crowd the keyword results.
                  Falls back to `query` if not provided.

    Steps:
      1. Semantic search with similarity_top_k=50 — broad candidate pool.
      2. Keyword/filename search for capitalized proper nouns (items, NPCs, locations).
      3. Mechanic term map — injects pages for lowercase mechanics the embedding
         model can't bridge (die→Hollowing, hollow→Human_Effigy, covenant→Covenants, …).
      4. Merge all results keyed by filename, boosting pages found by multiple methods.
      5. Return the top `top_k` (default 10) chunks formatted as context.
    """
    # Use raw_query for term extraction so player-stats labels don't pollute results
    term_query = raw_query if raw_query is not None else query

    # 1. Semantic search — use a large candidate pool (50) because ChromaDB's HNSW
    #    approximate search has poor recall at small k with this index size (~21k chunks).
    #    The hybrid merge below still trims to top_k (default 10) at the end.
    #    Expand stat abbreviations (INT→Intelligence etc.) so the embedding model
    #    can bridge short game-stat abbreviations to the full words in wiki text.
    retriever = index.as_retriever(similarity_top_k=50)
    semantic_nodes = retriever.retrieve(_expand_stat_abbrevs(query))

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

    # 4. Sort by combined score descending, keep top_k
    sorted_results = sorted(scored.values(), key=lambda x: x[2], reverse=True)[:top_k]

    context_parts = []
    for text, metadata, _score in sorted_results:
        source = metadata.get("file_name", "unknown")
        context_parts.append(f"--- Source: {source} ---\n{text}")

    return "\n\n".join(context_parts)


SYSTEM_PROMPT = """You are DS2 Scholar, a Dark Souls 2 companion AI grounded strictly in the Fextralife wiki context provided below.

The player is using Scholar of the First Sin (SotFS). When the wiki context contains SotFS-specific notes (marked with "Scholar of the First Sin" or "SotFS"), those apply to this player and should be preferred over vanilla DS2 information.

CRITICAL RULES — THESE OVERRIDE EVERYTHING ELSE:

1. ONLY use information from the "Wiki Context" block in the current message. This is an absolute constraint with zero exceptions.
2. Your training knowledge about Dark Souls 2 is COMPLETELY OFF-LIMITS — not for locations, NPC questlines, item stats, lore, boss strategies, or anything else.
3. EVEN IF you are 100% certain you know the correct answer from your training data, you MUST NOT use it. Certainty does not grant permission to use training knowledge.
4. Do NOT speculate, do NOT say "I believe" or "I think", do NOT add caveats like "from my previous knowledge" — just cite the wiki or admit the gap.
5. If a previous assistant message in the conversation stated something that is NOT supported by the CURRENT wiki context block, do not treat it as fact. Prior responses may have hallucinated; the current context block is the only source of truth.

WHEN CONTEXT IS INSUFFICIENT: respond with exactly — "The wiki context I retrieved doesn't cover that — I'd recommend checking the Fextralife wiki directly." Then stop. Do not add guesses or partial answers.

WHEN CONTEXT IS SUFFICIENT:
- Only state things directly supported by the wiki text. Do not add surrounding details from training.
- For directions: reference the nearest bonfire as a starting point.
- For build advice: consider the player's current stats and progression.
- Be concise but thorough. Use bullet points for lists of items or steps."""


def ask(index, question: str, chat_history: list = None, raw_question: str = None) -> str:
    """
    Ask a question using RAG + Claude.
    chat_history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    raw_question is the user's original question without any player stats preamble;
    it is used for keyword/term extraction so stat labels don't pollute results.
    """
    context = retrieve_context(index, question, raw_query=raw_question)

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


def stream_ask(index, question: str, chat_history: list = None, raw_question: str = None):
    """
    Ask a question using RAG + Claude, streaming the response.
    Yields text chunks as they arrive from the API.
    raw_question is the user's original question without any player stats preamble.
    """
    context = retrieve_context(index, question, raw_query=raw_question)

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
        for text in stream.text_stream:
            yield text


# Initialize index at module load time
print("Initializing DS2 Scholar RAG pipeline...")
index = get_index()
print("Ready.\n")
