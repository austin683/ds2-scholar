# RAG (Retrieval-Augmented Generation) pipeline for DS2 Scholar.
# Handles loading the knowledge base into ChromaDB, embedding queries,
# retrieving relevant documents, and generating answers via the Anthropic API.

import os
import re
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

# Use a free local embedding model — no OpenAI needed
EMBED_MODEL = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Cached list of all .md filenames in the knowledge base (populated on first use)
_KB_FILENAMES = None


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
        # Normalize: collapse _XX_ URL-encoding sequences (e.g. _27_ → '', _2C_ → '')
        # then collapse repeated underscores so both variants map to the same key.
        def _norm(fname: str) -> str:
            n = re.sub(r"_[0-9a-f]{2}_?", "_", fname.lower())
            return re.sub(r"_+", "_", n)

        seen: dict = {}  # norm_key → fname; later (alphabetically) wins
        for fname in sorted(all_files):
            seen[_norm(fname)] = fname  # plain _s_ sorts after _27s_, so it wins
        _KB_FILENAMES = list(seen.values())
    return _KB_FILENAMES


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
    "two hand":     ["Controls.md", "Combat.md"],
    "two-hand":     ["Controls.md", "Combat.md"],
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
    "sorcery":      ["Sorceries.md"],
    "sorceries":    ["Sorceries.md"],
    "miracle":      ["Miracles.md"],
    "miracles":     ["Miracles.md"],
    "pyromancy":    ["Pyromancies.md"],
    "pyromancies":  ["Pyromancies.md"],
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
    # NPCs — indirect item relationships the embedding model fails to bridge
    # "mcduff's workshop key" → the key is Bastille Key (Belfry Luna)
    "mcduff":              ["Bastille_Key.md", "Steady_Hand_McDuff.md", "McDuff_s_Workshop.md"],
    "blacksmith mcduff":   ["Steady_Hand_McDuff.md", "Bastille_Key.md"],
    "lenigrast":           ["Blacksmith_Lenigrast.md", "Lenigrast_s_Key.md"],
    "blacksmith lenigrast": ["Blacksmith_Lenigrast.md", "Lenigrast_s_Key.md"],
    "ornifex":             ["Weaponsmith_Ornifex.md"],
    "straid":              ["Straid_of_Olaphis.md"],
    "felkin":              ["Felkin_the_Outcast.md"],
    "carhillion":          ["Carhillion_of_the_Fold.md"],
    "rosabeth":            ["Rosabeth_of_Melfia.md"],
    "gavlan":              ["Gavlan.md", "Lonesome_Gavlan.md"],
    "lonesome gavlan":     ["Gavlan.md"],
}


def _mechanic_search(query: str) -> list:
    """
    Check the query against MECHANIC_TERM_MAP using word-boundary matching.
    Returns (content, metadata, score) tuples for ALL matched pages.
    Score is 0.9 for all mechanic map hits.

    Note: deliberately does NOT filter against already-seen files so that
    retrieve_context can always apply the score boost even for pages the
    semantic search already found (previously a bug where low-scoring
    semantic hits blocked the mechanic boost entirely).
    """
    MAX_CHARS = 3000
    query_lower = query.lower()
    files_to_add: list = []
    added_fnames: set = set()

    for trigger, fnames in MECHANIC_TERM_MAP.items():
        # Word-boundary check: trigger must appear as whole word(s) in query.
        # Allow optional trailing 's' so "mcduffs" matches "mcduff",
        # "gavlans" matches "gavlan", etc. (handles possessives without apostrophe).
        pattern = r"\b" + re.escape(trigger) + r"s?\b"
        if re.search(pattern, query_lower):
            for fname in fnames:
                if fname not in added_fnames and os.path.exists(
                    os.path.join(KNOWLEDGE_BASE_DIR, fname)
                ):
                    added_fnames.add(fname)
                    files_to_add.append((os.path.join(KNOWLEDGE_BASE_DIR, fname), fname))

    results = []
    for fpath, fname in files_to_add:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(MAX_CHARS)
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
    Exact matches score 1.0, fuzzy matches score 0.85.
    File content is capped at 3000 characters to avoid flooding context.
    """
    MAX_CHARS = 3000
    MAX_FUZZY_PER_TERM = 5
    results = []
    seen_paths: set = set()
    filenames = _get_kb_filenames()

    for term in terms:
        # --- Exact filename match ---
        candidate = term.replace(" ", "_") + ".md"
        exact_path = os.path.join(KNOWLEDGE_BASE_DIR, candidate)
        if os.path.exists(exact_path) and exact_path not in seen_paths:
            seen_paths.add(exact_path)
            with open(exact_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(MAX_CHARS)
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

            if all(w in fname_norm for w in term_words):
                seen_paths.add(fpath)
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(MAX_CHARS)
                results.append((content, {"file_name": fname}, 0.85))
                fuzzy_count += 1

    return results


def retrieve_context(index, query: str, top_k: int = 6, raw_query: str = None) -> str:
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
      5. Return the top `top_k` (default 6) chunks formatted as context.
    """
    # Use raw_query for term extraction so player-stats labels don't pollute results
    term_query = raw_query if raw_query is not None else query

    # 1. Semantic search — use a large candidate pool (50) because ChromaDB's HNSW
    #    approximate search has poor recall at small k with this index size (~21k chunks).
    #    The hybrid merge below still trims to top_k (default 6) at the end.
    retriever = index.as_retriever(similarity_top_k=50)
    semantic_nodes = retriever.retrieve(query)

    # Deduplicate by filename, keeping the highest-scoring chunk per file
    scored: dict = {}  # fname -> (text, metadata, score)
    for node in semantic_nodes:
        fname = node.metadata.get("file_name", "unknown")
        node_score = node.score or 0.0
        if fname not in scored or node_score > scored[fname][2]:
            scored[fname] = (node.text, node.metadata, node_score)

    # 2. Keyword/filename search (proper nouns — capitalized terms in raw question only)
    terms = extract_key_terms(term_query)
    if terms:
        for content, metadata, kw_score in _find_keyword_files(terms):
            fname = metadata.get("file_name", "unknown")
            if fname in scored:
                _prev_text, prev_meta, prev_score = scored[fname]
                # Prefer keyword content (top of file) over whatever chunk semantic
                # search happened to return — avoids empty/irrelevant chunks winning.
                scored[fname] = (content, prev_meta, prev_score + kw_score)
            else:
                scored[fname] = (content, metadata, kw_score)

    # 3. Mechanic term map (lowercase mechanics the embedding model can't bridge)
    for content, metadata, mech_score in _mechanic_search(term_query):
        fname = metadata.get("file_name", "unknown")
        if fname in scored:
            _prev_text, prev_meta, prev_score = scored[fname]
            scored[fname] = (content, prev_meta, prev_score + mech_score)
        else:
            scored[fname] = (content, metadata, mech_score)

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
