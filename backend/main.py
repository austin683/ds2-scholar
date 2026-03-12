# FastAPI application entry point for the Scholar backend.
# Defines API routes for querying the RAG pipeline and serving responses to the frontend.
# Supports multiple games in a single process — game_id is sent per-request from the frontend.

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

from backend.rag import ask, stream_ask, _INDEXES, _ALL_CONFIGS
from backend.utils import get_soul_memory_tier, format_player_context

app = FastAPI(title="Scholar API")

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

# All stat fields for all supported games — optional so any game subset works.
class PlayerStats(BaseModel):
    soul_level: Optional[int] = None
    # DS2 only
    soul_memory: Optional[int] = None
    vitality: Optional[int] = None
    attunement: Optional[int] = None
    adaptability: Optional[int] = None
    # Shared stats
    vigor: Optional[int] = None
    endurance: Optional[int] = None
    strength: Optional[int] = None
    dexterity: Optional[int] = None
    intelligence: Optional[int] = None
    faith: Optional[int] = None
    # ER only
    mind: Optional[int] = None
    arcane: Optional[int] = None
    # Shared
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
    game_id: str = "ds2"

class AskResponse(BaseModel):
    answer: str

class SoulMemoryRequest(BaseModel):
    soul_memory: int
    game_id: str = "ds2"


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/health")
def health():
    games = ", ".join(_ALL_CONFIGS.keys())
    return {"status": "ok", "message": f"Scholar RAG API ready (games: {games})"}


def _build_term_query(question: str, chat_history: Optional[list]) -> str:
    """
    Build the string used for keyword/term extraction (not for semantic search).

    Two enrichment cases:
    1. Pronoun follow-ups ("Where will he be?") — prepend the last user message
       so proper nouns from the previous turn carry into retrieval.
    2. Very short replies ("Yes", "Ok", "Sure") — prepend both the last user
       message AND the start of the last assistant message (capped at 400 chars).
       This ensures entity names mentioned by the assistant ("Winged Scythe",
       "Black Flame Blade") survive into the next retrieval call even when the
       user just confirms with a one-word reply.
    """
    if not chat_history:
        return question

    is_short_reply = len(question.strip().split()) <= 2
    has_pronoun = bool(re.search(r"\b(he|she|it|they|him|her|them|his|its|another)\b|any other\b", question, re.I))
    has_backref = bool(re.search(
        r"\b(i listed|i mentioned|those weapons|the ones i|what i said|from my list"
        r"|this boss|the boss|that boss|this fight|this enemy|this area|this dungeon"
        r"|the area i|my current area|where i am|area i.m in"
        r"|this weapon|this build|this item|this npc|this quest)\b",
        question, re.I))

    if not is_short_reply and not has_pronoun and not has_backref:
        return question

    # Gather last user and assistant messages in one pass
    prev_user = ""
    prev_assistant = ""
    for msg in reversed(chat_history):
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role == "user" and not prev_user:
            prev_user = msg.get("content", "")
        elif role == "assistant" and not prev_assistant:
            prev_assistant = msg.get("content", "")[:400]  # cap to avoid noise
        if prev_user and prev_assistant:
            break

    if not is_short_reply:
        # Pronoun or backreference follow-up: prepend previous user message so
        # entity names ("Morning Star", "Brick Hammer", etc.) survive into retrieval.
        return f"{prev_user} {question}" if prev_user else question

    # Short reply: include both sides of the last exchange so entity names
    # from the assistant's response (items, weapons, NPCs) survive into retrieval.
    parts = [p for p in [prev_user, prev_assistant, question] if p]
    return " ".join(parts)



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


def _enrich_term_query_for_build(term_query: str, player_stats, config) -> str:
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
    # Also trigger on very short queries (≤2 words) — these are almost always
    # conversational follow-ups ("Yes", "Ok", "Sure") that need weapon/build context
    # appended so the retrieval pipeline can find the right pages.
    is_short_reply = len(q_words) <= 2
    if not is_short_reply and not (q_words & config.build_question_words):
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
        config = _ALL_CONFIGS.get(request.game_id, _ALL_CONFIGS["ds2"])
        idx = _INDEXES[config.game_id]

        # Build question with player context if stats provided
        question = request.question
        if request.player_stats:
            stats_dict = request.player_stats.dict(exclude_none=True)
            print(f"[DEBUG] /ask player_stats received: {stats_dict}")
            if stats_dict:
                context = format_player_context(stats_dict, config)
                question = f"{context}\n\nQuestion: {request.question}"

        term_query = _build_term_query(request.question, request.chat_history)
        term_query = _enrich_term_query_for_build(term_query, request.player_stats, config)
        brief = _brief_player_summary(request.player_stats)
        answer = ask(idx, question, config=config, chat_history=request.chat_history, raw_question=term_query, brief_stats=brief)
        return AskResponse(answer=answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask-stream")
def ask_stream(request: AskRequest):
    """
    Streaming RAG endpoint. Returns Server-Sent Events with text chunks.
    """
    config = _ALL_CONFIGS.get(request.game_id, _ALL_CONFIGS["ds2"])
    idx = _INDEXES[config.game_id]

    question = request.question
    if request.player_stats:
        stats_dict = request.player_stats.dict(exclude_none=True)
        if stats_dict:
            context = format_player_context(stats_dict, config)
            question = f"{context}\n\nQuestion: {request.question}"

    term_query = _build_term_query(request.question, request.chat_history)
    term_query = _enrich_term_query_for_build(term_query, request.player_stats, config)
    brief = _brief_player_summary(request.player_stats)

    def generate():
        for chunk in stream_ask(idx, question, config=config, chat_history=request.chat_history, raw_question=term_query, brief_stats=brief):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # tells Varnish/nginx not to buffer SSE
        },
    )



@app.post("/soul-memory")
def check_soul_memory(request: SoulMemoryRequest):
    """
    Returns Soul Memory tier info and matchmaking range.
    Only available when the active game config includes a Soul Memory system.
    """
    config = _ALL_CONFIGS.get(request.game_id, _ALL_CONFIGS["ds2"])
    if config.soul_memory is None:
        raise HTTPException(status_code=404, detail="Soul Memory is not part of this game.")
    result = get_soul_memory_tier(request.soul_memory, config.soul_memory)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)