#!/usr/bin/env python3
"""
Rebuild the Scholar ChromaDB vector index.

Usage
-----
Full rebuild (wipe and re-index all files for a game):
    python scripts/rebuild_index.py --game ds2
    python scripts/rebuild_index.py --game er

Incremental rebuild (re-index only files changed since the last full build):
    python scripts/rebuild_index.py --game ds2 --changed
    python scripts/rebuild_index.py --game er --changed

The incremental mode compares .md file modification times against the
per-game timestamp file written by get_index() on a fresh build.  Use it
after editing a small number of .md files to avoid a multi-minute full rebuild.

Background
----------
The RAG pipeline has two data paths (see rag.py for details):

  PATH A — ChromaDB vector index  (semantic search)
    Built by this script or by get_index() on first run.
    Does NOT auto-update when .md files change.

  PATH B — raw .md file reads  (_mechanic_search, _find_keyword_files)
    Always reads the current file; reflects edits immediately.

Editing a .md file syncs PATH B instantly.  Run this script to sync PATH A.
"""

import argparse
import os
import shutil
import sys
import time

# Make sure project root is on the path so we can import backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llama_index.core import (
    Document,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# ── Paths (must match rag.py) ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "db")

EMBED_MODEL = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_stale_files(kb_dir: str, ts_file: str) -> list[str]:
    """Return .md filenames modified after the index was last built."""
    if not os.path.exists(ts_file):
        return []  # no timestamp → treat everything as current (or use full rebuild)
    try:
        built_at = float(open(ts_file).read().strip())
    except (ValueError, OSError):
        return []
    stale = []
    for fname in os.listdir(kb_dir):
        if fname.endswith(".md"):
            fpath = os.path.join(kb_dir, fname)
            if os.path.getmtime(fpath) > built_at:
                stale.append(fname)
    return stale


def _write_timestamp(ts_file: str) -> None:
    with open(ts_file, "w") as f:
        f.write(str(time.time()))


# ── Rebuild modes ─────────────────────────────────────────────────────────────

def full_rebuild(cfg) -> None:
    """Wipe the existing collection for this game and rebuild from all .md files."""
    collection_name = f"{cfg.game_id}_scholar"
    ts_file = os.path.join(DB_DIR, f".index_built_at_{cfg.game_id}")
    kb_dir = cfg.knowledge_base_dir

    # Only delete this game's collection, not the entire db/ dir (other games live there too)
    os.makedirs(DB_DIR, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=DB_DIR)
    try:
        chroma_client.delete_collection(collection_name)
        print(f"Deleted existing collection '{collection_name}'.")
    except Exception:
        pass  # didn't exist yet — that's fine

    print(f"Loading documents from {kb_dir} …")
    documents = SimpleDirectoryReader(kb_dir).load_data()
    print(f"Loaded {len(documents)} documents.")

    chroma_collection = chroma_client.get_or_create_collection(collection_name)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("Building index (this may take several minutes) …")
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=EMBED_MODEL,
        show_progress=True,
    )

    _write_timestamp(ts_file)
    print(f"\nFull rebuild complete. {chroma_collection.count()} chunks indexed.")


def incremental_rebuild(cfg) -> None:
    """Re-index only .md files modified since the last full build."""
    collection_name = f"{cfg.game_id}_scholar"
    ts_file = os.path.join(DB_DIR, f".index_built_at_{cfg.game_id}")
    kb_dir = cfg.knowledge_base_dir

    db_sqlite = os.path.join(DB_DIR, "chroma.sqlite3")
    if not os.path.exists(db_sqlite):
        print("No existing index found — falling back to full rebuild.")
        full_rebuild(cfg)
        return

    stale = _get_stale_files(kb_dir, ts_file)
    if not stale:
        print("Index is up to date — no .md files changed since the last build.")
        return

    print(f"Re-indexing {len(stale)} changed file(s):")
    for f in stale:
        print(f"  - {f}")

    chroma_client = chromadb.PersistentClient(path=DB_DIR)
    chroma_collection = chroma_client.get_or_create_collection(collection_name)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
        embed_model=EMBED_MODEL,
    )

    for fname in stale:
        fpath = os.path.join(kb_dir, fname)
        print(f"  {fname} … ", end="", flush=True)

        # Remove all existing chunks for this file from the collection.
        try:
            chroma_collection.delete(where={"file_name": {"$eq": fname}})
        except Exception:
            pass  # file may not have been indexed before; that's fine

        # Re-index the file as a new Document.
        with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        doc = Document(text=text, metadata={"file_name": fname})
        index.insert(doc)
        print("done")

    _write_timestamp(ts_file)
    print(f"\nIncremental rebuild complete. Index now has {chroma_collection.count()} chunks.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    from backend.configs.ds2 import DS2_CONFIG
    from backend.configs.er import ER_CONFIG
    _ALL_CONFIGS = {"ds2": DS2_CONFIG, "er": ER_CONFIG}
    game_choices = list(_ALL_CONFIGS.keys())

    parser = argparse.ArgumentParser(
        description="Rebuild a Scholar ChromaDB vector index.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--game",
        choices=game_choices,
        default="ds2",
        help=f"Which game's index to rebuild (default: ds2). Options: {', '.join(game_choices)}",
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Incremental mode: re-index only files modified since the last build.",
    )
    args = parser.parse_args()

    cfg = _ALL_CONFIGS[args.game]
    print(f"Target: {cfg.bot_name} ({args.game})")

    if args.changed:
        incremental_rebuild(cfg)
    else:
        full_rebuild(cfg)


if __name__ == "__main__":
    main()
