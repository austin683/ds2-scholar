# FastAPI application entry point for the DS2 Scholar backend.
# Defines API routes for querying the RAG pipeline and serving responses to the frontend.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag import ask, stream_ask, index
from backend.utils import get_soul_memory_tier, format_player_context

app = FastAPI(title="DS2 Scholar API")

# Allow React frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────

class PlayerStats(BaseModel):
    soul_level: Optional[int] = None
    soul_memory: Optional[int] = None
    vigor: Optional[int] = None
    endurance: Optional[int] = None
    vitality: Optional[int] = None
    attunement: Optional[int] = None
    strength: Optional[int] = None
    dexterity: Optional[int] = None
    adaptability: Optional[int] = None
    intelligence: Optional[int] = None
    faith: Optional[int] = None
    right_weapon_1: Optional[str] = None
    right_weapon_2: Optional[str] = None
    current_area: Optional[str] = None
    last_boss_defeated: Optional[str] = None
    build_type: Optional[str] = None
    notes: Optional[str] = None

class AskRequest(BaseModel):
    question: str
    player_stats: Optional[PlayerStats] = None
    chat_history: Optional[list] = None

class AskResponse(BaseModel):
    answer: str

class SoulMemoryRequest(BaseModel):
    soul_memory: int


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "message": "DS2 Scholar is ready."}


def _build_term_query(question: str, chat_history: Optional[list]) -> str:
    """
    Build the string used for keyword/term extraction (not for semantic search).
    Prepends the most recent user message from chat history so that follow-up
    queries using pronouns ("Where will he be?") still carry proper nouns
    ("Gavlan") from the previous turn.
    """
    if not chat_history:
        return question
    # Find the last user message in history
    for msg in reversed(chat_history):
        if isinstance(msg, dict) and msg.get("role") == "user":
            prev = msg.get("content", "")
            # Only prepend if the current question looks like a follow-up
            # (short, contains a pronoun, or has fewer than 3 capitalised words)
            import re as _re
            has_pronoun = bool(_re.search(r"\b(he|she|it|they|him|her|them|his|its)\b", question, _re.I))
            caps_count = len(_re.findall(r"\b[A-Z][a-z]{2,}", question))
            if has_pronoun or caps_count < 2:
                return f"{prev} {question}"
            break
    return question


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    """
    Main RAG endpoint. Accepts a question + optional player stats + chat history.
    Returns an answer grounded in the Fextralife wiki.
    """
    try:
        # Build question with player context if stats provided
        question = request.question
        if request.player_stats:
            stats_dict = request.player_stats.dict(exclude_none=True)
            print(f"[DEBUG] /ask player_stats received: {stats_dict}")
            if stats_dict:
                context = format_player_context(stats_dict)
                question = f"{context}\n\nQuestion: {request.question}"

        term_query = _build_term_query(request.question, request.chat_history)
        answer = ask(index, question, chat_history=request.chat_history, raw_question=term_query)
        return AskResponse(answer=answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask-stream")
def ask_stream(request: AskRequest):
    """
    Streaming RAG endpoint. Returns Server-Sent Events with text chunks.
    """
    question = request.question
    if request.player_stats:
        stats_dict = request.player_stats.dict(exclude_none=True)
        if stats_dict:
            context = format_player_context(stats_dict)
            question = f"{context}\n\nQuestion: {request.question}"

    term_query = _build_term_query(request.question, request.chat_history)

    def generate():
        for chunk in stream_ask(index, question, chat_history=request.chat_history, raw_question=term_query):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/soul-memory")
def check_soul_memory(request: SoulMemoryRequest):
    """
    Returns Soul Memory tier info and matchmaking range.
    """
    result = get_soul_memory_tier(request.soul_memory)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)