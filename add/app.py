"""
FastAPI wrapper for the circuit parameter-extraction agent.

Run:
    pip install fastapi "uvicorn[standard]" ollama python-dotenv
    python app.py
    # or: uvicorn app:app --host 127.0.0.1 --port 5000 --reload

Docs UI: http://localhost:5000/docs
"""

import threading
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import service

app = FastAPI(title="Circuit Agent API")

# Allow a browser frontend on another port (e.g. Vite/React dev server).
# Tighten allow_origins for anything beyond local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory sessions: {session_id: {"messages": [...], "lock": Lock}}
# Lost on restart; swap for Redis/DB if you need persistence.
_sessions: dict[str, dict] = {}
_sessions_guard = threading.Lock()


def _get_session(session_id: str | None) -> tuple[str, dict]:
    with _sessions_guard:
        if session_id and session_id in _sessions:
            return session_id, _sessions[session_id]
        sid = session_id or uuid.uuid4().hex
        _sessions[sid] = {
            "messages": service.new_conversation(),
            "lock": threading.Lock(),
        }
        return sid, _sessions[sid]


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


# Plain `def` (not async) on purpose: the Ollama client is blocking, so
# FastAPI runs these in its threadpool and the event loop stays free.
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    sid, session = _get_session(req.session_id)

    with session["lock"]:  # one in-flight turn per session
        session["messages"].append({"role": "user", "content": req.message.strip()})
        try:
            reply, circuits = service.run_turn(session["messages"])
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Model call failed: {e}")

    return ChatResponse(session_id=sid, reply=reply, circuits=circuits)


# --- Compatibility endpoint for the CircuitJS1 AIChatbotDialog ------------
# The dialog POSTs {"query": ...} to /query or /simple-query and expects
# {"success": bool, "response": str, "circuit_text": str?, "error": str?}.
# Both routes go to the agent, which decides for itself whether to ask a
# follow-up question or generate a circuit.
class DialogQuery(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: str | None = None


@app.post("/query")
@app.post("/simple-query")
def dialog_query(req: DialogQuery):
    sid, session = _get_session(req.session_id)

    with session["lock"]:
        session["messages"].append({"role": "user", "content": req.query.strip()})
        try:
            reply, circuits = service.run_turn(session["messages"])
        except Exception as e:
            return {"success": False, "error": str(e), "session_id": sid}

    out = {"success": True, "response": reply or "Done.", "session_id": sid}
    if circuits:
        out["circuit_text"] = circuits[-1]["netlist"]  # latest circuit only
    return out


@app.post("/reset/{session_id}")
def reset(session_id: str):
    with _sessions_guard:
        if session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Unknown session")
        _sessions[session_id]["messages"] = service.new_conversation()
    return {"session_id": session_id, "status": "reset"}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    with _sessions_guard:
        _sessions.pop(session_id, None)
    return {"session_id": session_id, "status": "deleted"}


@app.get("/health")
def health():
    return {"status": "ok", "model": service.MODEL, "tools": list(service.available_functions)}


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)