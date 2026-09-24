"""
FastAPI wrapper for the circuit parameter-extraction agent.

Run (from the `add/` directory):
    pip install -r requirements.txt
    python app.py
    # or: uvicorn app:app --host 127.0.0.1 --port 5000 --reload

Docs UI: http://localhost:5000/docs

Chat history: every session's transcript is saved to
    output/sessions/<session_id>.json
and served back by GET /history/<session_id>, so the chat dialog can restore
the conversation after it is closed and reopened (or the server restarts).
"""

import json
import os
import re
import threading
import time
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import service

app = FastAPI(title="Circuit Agent API")

# Allow the CircuitJS page (any origin) to call this server during local
# development. Tighten allow_origins for anything beyond that.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS_DIR = service.OUTPUT_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Session ids come from the client and end up in a file path, so only accept
# a safe character set (blocks "../" style tricks).
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# {session_id: {"messages": [...model context...], "transcript": [...], "lock": Lock}}
_sessions: dict[str, dict] = {}
_sessions_guard = threading.Lock()


# ---------------------------------------------------------------------------
# Transcript persistence
# ---------------------------------------------------------------------------

def _session_file(sid: str):
    return SESSIONS_DIR / f"{sid}.json"


def _load_transcript(sid: str) -> list[dict]:
    try:
        data = json.loads(_session_file(sid).read_text(encoding="utf-8"))
        return list(data.get("messages", []))
    except (OSError, ValueError, AttributeError):
        return []


def _save_transcript(sid: str, transcript: list[dict]) -> None:
    path = _session_file(sid)
    tmp = path.with_suffix(".tmp")
    payload = {
        "session_id": sid,
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "messages": transcript,
    }
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)  # atomic: never leaves a half-written file


def _get_session(session_id: str | None) -> tuple[str, dict]:
    if session_id and not _SID_RE.match(session_id):
        session_id = None

    with _sessions_guard:
        if session_id and session_id in _sessions:
            return session_id, _sessions[session_id]

        sid = session_id or uuid.uuid4().hex

        # Known id but not in memory (e.g. server restarted): rebuild the
        # model's context from the saved transcript.
        transcript = _load_transcript(sid)
        messages = service.new_conversation()
        for m in transcript:
            if m.get("role") in ("user", "assistant") and m.get("text"):
                messages.append({"role": m["role"], "content": m["text"]})

        _sessions[sid] = {
            "messages": messages,
            "transcript": transcript,
            "lock": threading.Lock(),
        }
        return sid, _sessions[sid]


def _handle_turn(session_id: str | None, text: str) -> tuple[str, str, list[dict]]:
    """Run one user turn, record it in the transcript, return (sid, reply, circuits)."""
    sid, session = _get_session(session_id)

    with session["lock"]:  # one in-flight turn per session
        text = text.strip()
        mark = len(session["messages"])
        session["messages"].append({"role": "user", "content": text})
        try:
            reply, circuits = service.run_turn(session["messages"])
        except Exception:
            del session["messages"][mark:]  # don't leave a dangling user turn
            raise

        reply = reply or "Done."
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        session["transcript"].append({"role": "user", "text": text, "time": now})
        entry = {"role": "assistant", "text": reply, "time": now}
        if circuits:
            entry["circuit"] = circuits[-1]["netlist"]  # latest circuit only
        session["transcript"].append(entry)

        try:
            _save_transcript(sid, session["transcript"])
        except OSError as e:
            print(f"Warning: could not save transcript for {sid}: {e}")

    return sid, reply, circuits


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class Circuit(BaseModel):
    circuit: str
    arguments: dict
    saved_to: str
    netlist: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    circuits: list[Circuit]


class DialogQuery(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

# Plain `def` (not async) on purpose: the Ollama client is blocking, so
# FastAPI runs these in its threadpool and the event loop stays free.
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        sid, reply, circuits = _handle_turn(req.session_id, req.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model call failed: {e}")
    return ChatResponse(session_id=sid, reply=reply, circuits=circuits)


# Compatibility endpoint for the CircuitJS1 AIChatbotDialog:
# {"query": ...} in, {"success", "response", "circuit_text"?, "error"?} out.
@app.post("/query")
@app.post("/simple-query")
def dialog_query(req: DialogQuery):
    try:
        sid, reply, circuits = _handle_turn(req.session_id, req.query)
    except Exception as e:
        return {"success": False, "error": str(e), "session_id": req.session_id}

    out = {"success": True, "response": reply, "session_id": sid}
    if circuits:
        out["circuit_text"] = circuits[-1]["netlist"]
    return out


@app.get("/history/{session_id}")
def history(session_id: str):
    """Transcript for a session (empty list if unknown) so the dialog can restore it."""
    if not _SID_RE.match(session_id):
        raise HTTPException(status_code=404, detail="Unknown session")
    with _sessions_guard:
        session = _sessions.get(session_id)
        messages = list(session["transcript"]) if session else _load_transcript(session_id)
    return {"session_id": session_id, "messages": messages}


@app.post("/reset/{session_id}")
def reset(session_id: str):
    """Forget the conversation and delete its saved transcript."""
    if not _SID_RE.match(session_id):
        raise HTTPException(status_code=404, detail="Unknown session")
    with _sessions_guard:
        session = _sessions.get(session_id)
    if session:
        with session["lock"]:
            session["messages"] = service.new_conversation()
            session["transcript"] = []
    _session_file(session_id).unlink(missing_ok=True)
    return {"session_id": session_id, "status": "reset"}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if not _SID_RE.match(session_id):
        raise HTTPException(status_code=404, detail="Unknown session")
    with _sessions_guard:
        _sessions.pop(session_id, None)
    _session_file(session_id).unlink(missing_ok=True)
    return {"session_id": session_id, "status": "deleted"}


@app.get("/health")
def health():
    return {"status": "ok", "model": service.MODEL, "tools": list(service.available_functions)}


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)