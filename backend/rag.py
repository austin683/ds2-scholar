# RAG (Retrieval-Augmented Generation) pipeline for DS2 Scholar.
# Handles loading the knowledge base into ChromaDB, embedding queries,
# retrieving relevant documents, and generating answers via the Anthropic API.

import os
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

def retrieve_context(index, query: str, top_k: int = 6) -> str:
    """Retrieve the most relevant wiki chunks for a query."""
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    
    context_parts = []
    for i, node in enumerate(nodes):
        source = node.metadata.get("file_name", "unknown")
        context_parts.append(f"--- Source: {source} ---\n{node.text}")
    
    return "\n\n".join(context_parts)

def ask(index, question: str, chat_history: list = None) -> str:
    """
    Ask a question using RAG + Claude.
    chat_history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    """
    # Get relevant wiki context
    context = retrieve_context(index, question)

    # Build system prompt
    system_prompt = """You are DS2 Scholar, an expert Dark Souls 2 companion AI. 
You have access to the complete Fextralife Dark Souls 2 wiki as your knowledge base.

Your job is to give accurate, helpful answers about Dark Souls 2 based ONLY on the wiki context provided.
If the context doesn't contain enough information to answer confidently, say so rather than guessing.

When giving directions, always reference the nearest bonfire as a starting point.
When giving build advice, consider the player's current stats and progression.
Be concise but thorough. Use bullet points for lists of items or steps."""

    # Build messages
    messages = []
    
    # Add chat history if provided
    if chat_history:
        messages.extend(chat_history)
    
    # Add current question with context
    messages.append({
        "role": "user",
        "content": f"""Wiki Context:
{context}

Question: {question}"""
    })

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=messages
    )

    return response.content[0].text


def stream_ask(index, question: str, chat_history: list = None):
    """
    Ask a question using RAG + Claude, streaming the response.
    Yields text chunks as they arrive from the API.
    """
    context = retrieve_context(index, question)

    system_prompt = """You are DS2 Scholar, an expert Dark Souls 2 companion AI.
You have access to the complete Fextralife Dark Souls 2 wiki as your knowledge base.

Your job is to give accurate, helpful answers about Dark Souls 2 based ONLY on the wiki context provided.
If the context doesn't contain enough information to answer confidently, say so rather than guessing.

When giving directions, always reference the nearest bonfire as a starting point.
When giving build advice, consider the player's current stats and progression.
Be concise but thorough. Use bullet points for lists of items or steps."""

    messages = []

    if chat_history:
        messages.extend(chat_history)

    messages.append({
        "role": "user",
        "content": f"""Wiki Context:
{context}

Question: {question}"""
    })

    with claude.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=messages
    ) as stream:
        for text in stream.text_stream:
            yield text


# Initialize index at module load time
print("Initializing DS2 Scholar RAG pipeline...")
index = get_index()
print("Ready.\n")