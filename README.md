# DS2 Scholar

A Retrieval-Augmented Generation (RAG) application for the Dark Souls 2 wiki.

## Overview

DS2 Scholar scrapes the DS2 wiki into a local knowledge base, indexes it with ChromaDB, and exposes a FastAPI backend that uses the Anthropic API to answer natural-language questions about items, bosses, lore, and mechanics.

## Project Structure

```
ds2_scholar/
├── scraper/          # Wiki scraper that builds the knowledge base
├── backend/          # FastAPI app + RAG pipeline
├── frontend/         # UI (TBD)
├── knowledge_base/   # Scraped wiki content (gitignored)
├── db/               # ChromaDB vector store (gitignored)
├── .env              # API keys (gitignored)
└── requirements.txt
```

## Setup

1. Add your Anthropic API key to `.env`.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the scraper to populate `knowledge_base/`.
4. Start the backend: `uvicorn backend.main:app --reload`
