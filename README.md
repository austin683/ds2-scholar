# DS2 Scholar

A RAG-powered Dark Souls 2: Scholar of the First Sin companion chatbot. Ask natural-language questions about items, bosses, builds, lore, mechanics, NPCs, and locations — grounded entirely in the Fextralife DS2 wiki. Optionally set your player stats for personalized answers.

## Stack

- **Backend**: FastAPI (port 8001)
- **Embeddings**: BGE-small-en-v1.5 via LlamaIndex (runs locally)
- **Vector DB**: ChromaDB (HNSW, ~21k chunks)
- **Generation**: Anthropic `claude-sonnet-4-6`
- **Frontend**: React + Tailwind (port 3001)

## Setup

```bash
# 1. Install Python dependencies
pip3 install -r requirements.txt

# 2. Install frontend dependencies
cd frontend && npm install && cd ..

# 3. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# 4. Scrape the wiki (takes ~1.5–2 hours)
python3 scraper/ds2_scraper.py

# 5. Start the backend (builds ChromaDB index on first run)
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8001

# 6. Start the frontend (separate terminal)
cd frontend && npm start
```

## Project Structure

```text
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
├── .env                    # ANTHROPIC_API_KEY (gitignored)
└── requirements.txt
```

## Features

- Hybrid search: semantic similarity + keyword filename matching + mechanic term map
- Player stats sidebar (Soul Level, class, all 9 stats) — responses adapt to your build
- Streaming responses via SSE
- `/level` command — modal showing soul costs to next Soul Memory tier
- Slash command interface (type `/`)
- Strict wiki-grounded answers — no hallucination from training knowledge
