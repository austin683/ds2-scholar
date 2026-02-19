#!/usr/bin/env python3
"""
Rebuild the DS2 Scholar ChromaDB vector index.

Usage
-----
Full rebuild (wipe everything and re-index all files — always correct):
    python scripts/rebuild_index.py

Incremental rebuild (re-index only files changed since the last full build):
    python scripts/rebuild_index.py --changed

The incremental mode compares .md file modification times against the
INDEX_TIMESTAMP_FILE written by get_index() on a fresh build.  Use it after
editing a small number of .md files to avoid a multi-minute full rebuild.

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
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# ── Paths (must match rag.py) ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
DB_DIR = os.path.join(BASE_DIR, "db")
INDEX_TIMESTAMP_FILE = os.path.join(DB_DIR, ".index_built_at")

EMBED_MODEL = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_stale_files() -> list[str]:
    """Return .md filenames modified after the index was last built."""
    if not os.path.exists(INDEX_TIMESTAMP_FILE):
        return []  # no timestamp → treat everything as current (or use full rebuild)
    try:
        built_at = float(open(INDEX_TIMESTAMP_FILE).read().strip())
    except (ValueError, OSError):
        return []
    stale = []
    for fname in os.listdir(KNOWLEDGE_BASE_DIR):
        if fname.endswith(".md"):
            fpath = os.path.join(KNOWLEDGE_BASE_DIR, fname)
            if os.path.getmtime(fpath) > built_at:
                stale.append(fname)
    return stale


def _write_timestamp() -> None:
    with open(INDEX_TIMESTAMP_FILE, "w") as f:
        f.write(str(time.time()))


# ── Rebuild modes ─────────────────────────────────────────────────────────────

def full_rebuild() -> None:
    """Wipe the existing index and rebuild from all .md files."""
    if os.path.exists(DB_DIR):
        print(f"Removing existing index at {DB_DIR} …")
        shutil.rmtree(DB_DIR)
    os.makedirs(DB_DIR)

    print(f"Loading documents from {KNOWLEDGE_BASE_DIR} …")
    documents = SimpleDirectoryReader(KNOWLEDGE_BASE_DIR).load_data()
    print(f"Loaded {len(documents)} documents.")

    chroma_client = chromadb.PersistentClient(path=DB_DIR)
    chroma_collection = chroma_client.get_or_create_collection("ds2_scholar")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("Building index (this may take several minutes) …")
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=EMBED_MODEL,
        show_progress=True,
    )

    _write_timestamp()
    print(f"\nFull rebuild complete. {chroma_collection.count()} chunks indexed.")


def incremental_rebuild() -> None:
    """Re-index only .md files modified since the last full build."""
    db_sqlite = os.path.join(DB_DIR, "chroma.sqlite3")
    if not os.path.exists(db_sqlite):
        print("No existing index found — falling back to full rebuild.")
        full_rebuild()
        return

    stale = _get_stale_files()
    if not stale:
        print("Index is up to date — no .md files changed since the last build.")
        return

    print(f"Re-indexing {len(stale)} changed file(s):")
    for f in stale:
        print(f"  - {f}")

    chroma_client = chromadb.PersistentClient(path=DB_DIR)
    chroma_collection = chroma_client.get_or_create_collection("ds2_scholar")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
        embed_model=EMBED_MODEL,
    )

    for fname in stale:
        fpath = os.path.join(KNOWLEDGE_BASE_DIR, fname)
        print(f"  {fname} … ", end="", flush=True)

        # Remove all existing chunks for this file from the collection.
        # ChromaDB metadata uses "file_name" (set by SimpleDirectoryReader).
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

    _write_timestamp()
    print(f"\nIncremental rebuild complete. Index now has {chroma_collection.count()} chunks.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild the DS2 Scholar ChromaDB vector index.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Incremental mode: re-index only files modified since the last build.",
    )
    args = parser.parse_args()

    if args.changed:
        incremental_rebuild()
    else:
        full_rebuild()


if __name__ == "__main__":
    main()
