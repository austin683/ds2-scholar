# DS2 Scholar — Project Handoff

## What This Is

A RAG-powered Dark Souls 2: Scholar of the First Sin companion chatbot. It scrapes the Fextralife DS2 wiki into a local knowledge base, indexes it with ChromaDB, and uses Claude claude-sonnet-4-6 to answer natural-language questions about items, bosses, builds, lore, mechanics, NPCs, locations, etc.

The user can set their player stats (Soul Level, class, VGR/END/VIT/ATN/STR/DEX/ADP/INT/FTH) and the system tailors responses accordingly ("can I wield this weapon?", "what should I level next?").

Strictly Scholar of the First Sin — no vanilla DS2 toggle. Claude is instructed to prefer SotFS-specific wiki notes.

---

## Stack

- **Backend**: FastAPI on port 8001
- **Embeddings**: BGE-small-en-v1.5 via LlamaIndex 0.10.68 (runs locally)
- **Vector DB**: ChromaDB 0.4.24 (HNSW index, ~21k chunks)
- **Generation**: Anthropic `claude-sonnet-4-6`
- **Frontend**: React on port 3001 (Tailwind, dark DS2 theme)

---

## Project Structure

```
ds2_scholar/
├── scraper/
│   ├── ds2_scraper.py      # Full wiki crawler
│   └── test_scraper.py     # Test scraper (saves to knowledge_base_test/)
├── backend/
│   ├── main.py             # FastAPI routes: /ask, /ask-stream, /soul-memory
│   ├── rag.py              # Hybrid RAG pipeline (semantic + keyword + term map)
│   └── utils.py            # Soul Memory tier checker, player stats formatter
├── frontend/src/
│   └── App.js              # React chat UI
├── knowledge_base/         # Scraped wiki .md files (gitignored)
├── db/                     # ChromaDB vector store (gitignored)
├── .env                    # ANTHROPIC_API_KEY
└── requirements.txt
```

---

## How to Run

```bash
# Start backend
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8001

# Start frontend (separate terminal)
cd frontend && npm start
```

---

## Architecture

### Scraper (`scraper/ds2_scraper.py`)

Crawls Fextralife DS2 wiki from ~18 seed pages (Weapons, Armor, Bosses, Locations, NPCs, Rings, Items, Magic, Hexes, etc.) and follows all internal links. Saves each page as a `.md` file in `knowledge_base/`.

Key design decisions:

- **Custom table parser** — resolves HTML rowspan/colspan into a 2D grid, detects table type, and converts to clean markdown. `html2text` handles all non-table content.
- **Weapon upgrade tables** — injected with known column headers (`Phys Atk`, `STR Scaling`, etc.) since Fextralife's sub-header row is icon-only (blank after HTML parsing).
- **Stats widget** — extracted as prose lines (`Requirements: STR 10, DEX 12`, `Weapon Type: Straight Sword`) instead of a noisy table blob.
- **Footer cutoff** — strips everything after "Join the page discussion" and similar phrases.
- **SKIP_PATTERNS** — URL-pattern filter for Fextralife meta/community pages (Media, Gallery, Forum, Fan Art, etc.).
- **1.5s delay** between requests; resumes safely (skips already-downloaded files).

### RAG Pipeline (`backend/rag.py`)

Hybrid search: semantic (HNSW top-50) + keyword (filename matching) + mechanic term map.

- `retrieve_context(index, query, raw_query=None)`:
  - Semantic search uses the **full augmented query** (includes player stats preamble — helps embedding context)
  - Keyword/term extraction uses **`raw_query`** (original question only) — prevents stat labels like "Soul Level" from polluting keyword results
- `MECHANIC_TERM_MAP` — 60+ entries mapping lowercase mechanic terms ("poise", "agility", "adaptability", "twinkling titanite") to their wiki filenames
- `similarity_top_k=50` — HNSW has poor recall at small k for this index size
- `_get_kb_filenames()` — deduplicates URL-encoded filename variants (e.g. `McDuff_27s_Workshop.md` vs `McDuff%27s_Workshop.md`)

### Backend (`backend/main.py`)

- `/ask` — standard request/response
- `/ask-stream` — SSE streaming response
- `/soul-memory` — returns the soul memory tier for a given soul count

`_build_term_query()` prepends the last user message to pronoun follow-ups ("Where will he be?" → "Tell me about Gavlan Where will he be?") so proper nouns survive context collapse across turns.

### Training Knowledge Guard

System prompt has explicit numbered rules forbidding use of Claude's training knowledge. If the retrieved wiki context doesn't cover something, the response is:

> "The wiki context I retrieved doesn't cover that — I'd recommend checking the Fextralife wiki directly."

No partial guesses. Known data gaps (e.g. Gavlan's Huntsman's Copse location missing from wiki) are answered with "I don't know" — only fix is manually patching the `.md` file.

### Frontend

- Sidebar with player stats input (Soul Level, class, all 9 stats + equipment fields)
- Streaming chat via SSE
- `/level` slash command — modal showing stat costs to next Soul Memory tier
- Slash command menu (type `/`)
- Home screen with suggested questions
- Placeholder: "Ask the Scholar... (Enter to send, Shift+Enter for new line, / for commands)"

---

## Current State

A fresh full crawl just completed (knowledge base was cleared and rebuilt with an improved scraper that correctly handles weapon stat tables). The ChromaDB index needs to be rebuilt from the new `.md` files on next backend startup.

---

## Open Question for Review

**Which `.md` files in the knowledge base are likely pure noise worth removing before indexing?**

During the crawl, pages like these were observed:

- `Playstation_Network_ID_PSN`
- `Xbox_Live_Gamertags`
- `YouTube_Partners`
- `Events`

The PSN/Xbox pages may actually be useful — they could answer multiplayer questions like "what name shows up when I summon someone?" So they're not obviously junk.

We're looking for a principled approach to auditing ~2,500 files. The goal:

- **Keep**: anything that could plausibly answer a DS2 gameplay question, including multiplayer, covenants, online mechanics, and community features that affect gameplay
- **Cut**: Fextralife site-meta content (staff pages, wiki request pages, affiliate/partner pages) with zero game knowledge value

What filename patterns or categories are reliably useless for a DS2 game guide RAG? And conversely, which categories look like noise but actually contain useful game info?
