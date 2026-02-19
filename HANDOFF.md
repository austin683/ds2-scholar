# DS2 Scholar — Project Handoff

## What This Is
A RAG-powered Dark Souls 2 companion app that answers build questions, locates items and bonfires, and provides accurate game knowledge grounded in the Fextralife wiki. Built with LlamaIndex, ChromaDB, FastAPI, React, and Claude Sonnet.

---

## Project Structure
```
ds2_scholar/
├── scraper/
│   └── ds2_scraper.py          # Full wiki crawler (html2text, BeautifulSoup)
├── backend/
│   ├── main.py                 # FastAPI app, /ask, /ask-stream, /soul-memory endpoints
│   ├── rag.py                  # LlamaIndex RAG pipeline, ChromaDB, Claude API
│   └── utils.py                # Soul Memory tier checker, player stats context builder
├── frontend/
│   └── src/
│       └── App.js              # React chat UI with Tailwind
├── knowledge_base/             # 2,518 scraped Fextralife DS2 wiki pages as .md files
├── db/                         # ChromaDB vector database (21,613 chunks)
├── tests/
│   └── test_api.py             # 9 passing API tests
├── .env                        # ANTHROPIC_API_KEY (never commit)
├── requirements.txt
├── start.sh                    # Launches both backend and frontend
├── stop.sh                     # Kills both processes
└── README.md
```

---

## How to Run
```bash
# Install Python dependencies
pip3 install llama-index-core==0.10.68 llama-index-readers-file==0.1.33 \
  llama-index-vector-stores-chroma==0.1.10 llama-index-embeddings-huggingface==0.2.3 \
  chromadb==0.4.24 anthropic fastapi uvicorn python-dotenv sentence-transformers \
  beautifulsoup4 html2text requests

# Install frontend dependencies
cd frontend && npm install

# Set API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# Launch everything
chmod +x start.sh stop.sh
./start.sh
```

Backend runs on `http://localhost:8001`
Frontend runs on `http://localhost:3001`

---

## Architecture

### RAG Pipeline (backend/rag.py)
- **Embedding model:** `BAAI/bge-small-en-v1.5` (free, runs locally via HuggingFace)
- **Vector DB:** ChromaDB persisted to `db/` folder
- **LLM:** Claude Sonnet (`claude-sonnet-4-6`) via Anthropic API
- **Chunks retrieved:** top_k=6 per query
- **Index:** Built once from knowledge_base/, loads from disk on subsequent runs (~21,613 chunks)
- **Streaming:** `/ask-stream` endpoint uses SSE for real-time streaming responses

### Player Stats Injection
Every query automatically includes player stats from the sidebar via `format_player_context()` in `utils.py`. Stats are sent as `player_stats` in the request body and injected into the prompt before hitting Claude.

### API Endpoints
- `GET /health` — health check
- `POST /ask` — standard RAG query with optional player_stats and chat_history
- `POST /ask-stream` — streaming SSE version of /ask
- `POST /soul-memory` — Soul Memory tier checker

---

## Frontend Features
- Dark DS2-themed UI with gold accents (Tailwind)
- Collapsible stats sidebar with all 9 DS2 stats + equipment fields
- Stat icons next to each stat label
- `/level` modal — opens when user types /level, shows all stats with +/- inputs, soul cost estimator, confirm/cancel
- `/undo` command — planned, not yet implemented
- Slash command interface showing all available commands
- Soul Memory tier checker button posts result as chat bubble
- Streaming responses via SSE (text appears word by word)
- Markdown rendering with remark-gfm (tables, bold, headers, lists)
- Auto-scroll to latest message
- Enter to send, Shift+Enter for new line
- Quick action buttons on empty chat state

---

## Known Issues / Tomorrow's TODO

### High Priority
1. **Re-scrape with better table parsing** — HTML weapon stat tables got mangled during scraping. `html2text` doesn't handle complex nested tables well. Need to rewrite scraper to detect tables and use BeautifulSoup's table parser directly, then re-run the full scrape and rebuild ChromaDB index.

2. **Hybrid search** — Currently using pure semantic similarity search. When user asks about specific items (e.g. "Bastille Key location"), the RAG pulls general area pages instead of the specific item page. Fix: combine semantic search with keyword/BM25 search so exact item name matches get boosted. LlamaIndex supports hybrid retrieval.

### Medium Priority
3. **`/undo` command** — Roll back last `/level` changes. Store previous stat state before each `/level` confirmation and restore it on `/undo`.

4. **ngrok setup** — For sharing with non-technical friend. Run `ngrok http 8001`, update frontend API URL to ngrok address. Add simple token auth to prevent API key abuse.

5. **Logo polish** — Custom DS2-themed favicon/logo. Current one has white background issue in browser tab.

### Nice to Have
6. **AR Calculator** — Was planned but deprioritized. DS2 damage formula is complex, needs accurate per-stat scaling curves. Would need user to input Dark Bonus from character screen directly rather than calculating from INT/FTH. Re-visit after hybrid search is solid.

---

## Scraper Notes

### Current Scraper (scraper/ds2_scraper.py)
- Starts from 18 seed pages (Weapons, Magic, Hexes, Armor, etc.)
- Crawls all internal DS2 wiki links automatically
- Skips junk pages (forums, media, fan art, etc.)
- Cleans nav junk from top and comments from bottom of each page
- Saves as .md files to knowledge_base/
- 1.5 second delay between requests
- Skips already-downloaded pages (safe to re-run)
- Final count: 2,518 pages scraped, 362 skipped

### Re-scrape Plan for Tomorrow
The main issue is weapon stat tables. Need to:
1. Add a table detection step in `scrape_page()` using BeautifulSoup
2. When a `<table>` is found, parse it manually into clean markdown columns
3. Use `soup.find_all('table')` and convert each row to `| col1 | col2 | col3 |` format
4. Wipe `knowledge_base/` and `db/` folders
5. Re-run scraper
6. Rebuild ChromaDB index (takes ~15 minutes)

---

## Environment
- Python 3.9.6 (macOS system Python)
- Node 18+
- macOS (Sonnet, Apple Silicon)
- ChromaDB 0.4.24 (pinned — newer versions incompatible with llama-index-core 0.10.68)
- LlamaIndex core 0.10.68 (pinned — version conflicts with newer releases)

---

## Key Files to Know

**backend/rag.py** — The brain. `get_index()` builds/loads ChromaDB. `retrieve_context()` pulls relevant chunks. `ask()` and `stream_ask()` call Claude with retrieved context + player stats.

**backend/utils.py** — `get_soul_memory_tier()` for matchmaking info. `format_player_context()` converts sidebar stats dict into a formatted string injected into every query.

**backend/main.py** — FastAPI routes. Player stats are deserialized via `PlayerStats` Pydantic model and passed to `format_player_context()` before hitting the RAG.

**frontend/src/App.js** — All UI state. `buildPlayerStats()` maps short frontend keys (vgr, end, str) to long Pydantic model keys (vigor, endurance, strength) before sending to backend. `handleSend()` uses fetch() with streaming for `/ask-stream`.

**scraper/ds2_scraper.py** — Full wiki crawler. `clean_markdown()` strips nav and comments. `get_wiki_links()` only follows DS2 wiki internal links. `SKIP_PATTERNS` filters junk pages.

---

## Model
- **Current:** `claude-sonnet-4-6`
- **Was:** `claude-opus-4-6` (switched to Sonnet for speed, no quality loss for RAG use case)
- **Haiku** is an option if speed is still an issue after hybrid search

---

## Deployment Plan (Future)
- Backend: Railway or Render (free tier, supports FastAPI)
- Frontend: Vercel or Netlify (free, one-click from GitHub)
- Problem: ChromaDB and knowledge_base are local — need cloud vector DB solution for real deployment
- Short term: ngrok for friend sharing while running locally
- Catalyst option was considered but requires architecture rewrite for cloud vector DB

