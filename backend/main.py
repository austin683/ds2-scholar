# FastAPI application entry point for the DS2 Scholar backend.
# Defines API routes for querying the RAG pipeline and serving responses to the frontend.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import sys
import os
import re
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag import ask, stream_ask, index
from backend.utils import get_soul_memory_tier, format_player_context

app = FastAPI(title="DS2 Scholar API")

# Allow React frontend to talk to backend.
# ALLOWED_ORIGINS is a comma-separated list of origins (no trailing slashes).
# Add the Vercel URL and any ngrok URLs to the env var when running for remote access.
# e.g. ALLOWED_ORIGINS=https://ds2-scholar.vercel.app,http://localhost:3001
_default_origins = "http://localhost:3000,http://localhost:3001,http://localhost:8001"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
            # Only prepend if the current question contains a pronoun — this catches
            # genuine follow-ups like "Where will he be?" or "What does it drop?"
            # without injecting irrelevant entity names from the previous turn into
            # unrelated questions (e.g. "what weapons drop here?" after a boss question).
            import re as _re
            has_pronoun = bool(_re.search(r"\b(he|she|it|they|him|her|them|his|its)\b", question, _re.I))
            if has_pronoun:
                return f"{prev} {question}"
            break
    return question


# Words that signal a build/stat/leveling question — triggers stat context enrichment
_BUILD_QUESTION_WORDS = {
    "level", "levels", "leveling", "stat", "stats", "build", "upgrade", "invest",
    "prioritize", "next", "should", "recommend", "advice", "improve",
    "focus", "pump", "raise", "increase", "cap", "priority", "put",
    "stronger", "points", "spend", "allocate",
    "weapon", "weapons", "infuse", "infusion", "infusing", "swap", "switch",
}


def _brief_player_summary(player_stats) -> str:
    """
    Compact one-line summary of player stats for the Haiku rewriter prompt.
    e.g. "STR build, SL62, Greatsword +2, Lost Bastille"
    """
    if not player_stats:
        return ""
    parts = []
    if player_stats.build_type:
        parts.append(f"{player_stats.build_type} build")
    if player_stats.soul_level:
        parts.append(f"SL{player_stats.soul_level}")
    if player_stats.right_weapon_1:
        parts.append(player_stats.right_weapon_1)
    if player_stats.right_weapon_2:
        parts.append(player_stats.right_weapon_2)
    if player_stats.current_area:
        parts.append(player_stats.current_area)
    return ", ".join(parts)


def _enrich_term_query_for_build(term_query: str, player_stats) -> str:
    """
    When the question is build/stat adjacent and player stats are set, append
    the player's build type and primary weapon to the term query.

    This causes the mechanic map to fire for the relevant stat pages
    (e.g. build_type "Str" → "str" trigger → Strength.md + Stat_Scaling.md)
    and keyword search to find the weapon page — even when the question itself
    ("what should I level next?") contains no capitalized entity names.

    Only activates for build-adjacent questions to avoid cluttering context
    for unrelated queries like location or boss questions.
    """
    if not player_stats:
        return term_query

    q_words = set(re.sub(r"[^a-z\s]", "", term_query.lower()).split())
    if not q_words & _BUILD_QUESTION_WORDS:
        return term_query

    extras = []

    # Build type → hits mechanic map (e.g. "str" → Strength.md + Stat_Scaling.md)
    if player_stats.build_type:
        extras.append(player_stats.build_type.lower())

    # Both weapons → hits keyword search for weapon pages (strip +X upgrade suffix)
    for weapon in [player_stats.right_weapon_1, player_stats.right_weapon_2]:
        if weapon:
            weapon_clean = re.sub(r"\s*\+\d+$", "", weapon).strip()
            if weapon_clean:
                extras.append(weapon_clean)

    return f"{term_query} {' '.join(extras)}" if extras else term_query


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
        term_query = _enrich_term_query_for_build(term_query, request.player_stats)
        brief = _brief_player_summary(request.player_stats)
        answer = ask(index, question, chat_history=request.chat_history, raw_question=term_query, brief_stats=brief)
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
    term_query = _enrich_term_query_for_build(term_query, request.player_stats)
    brief = _brief_player_summary(request.player_stats)

    def generate():
        for chunk in stream_ask(index, question, chat_history=request.chat_history, raw_question=term_query, brief_stats=brief):
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