"""POST /chat: runs the LangGraph workflow and streams progress + live form updates over SSE."""
import json
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..ai.graph import graph
from ..db import SessionLocal
from ..models import Investigation, Message
from ..schemas import ChatRequest, InvestigationData
from ..services.persist import derive_title, snapshot, validated, write_audit

router = APIRouter(prefix="/api/investigations", tags=["chat"])

NODE_LABELS = {
    "route": "Understanding your request",
    "ingest": "Extracting fields from the incident",
    "edit": "Applying your correction",
    "hypothesize": "Building hypotheses and 5 Whys",
    "critic": "Challenging the reasoning",
    "plan": "Finding missing evidence and drafting CAPA",
    "answer": "Answering",
    "finalize": "Scoring evidence sufficiency",
}


def sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


@router.post("/{inv_id}/chat")
async def chat(inv_id: int, req: ChatRequest):
    with SessionLocal() as db:
        if not db.get(Investigation, inv_id):
            raise HTTPException(404, "Investigation not found")
    if not (req.message.strip() or req.document_text or req.action):
        raise HTTPException(400, "Empty request")

    async def stream():
        with SessionLocal() as db:
            inv = db.get(Investigation, inv_id)
            original = inv.data
            user_text = req.message.strip() or (f"[uploaded {req.document_name}]" if req.document_text else f"[{req.action}]")
            state = {
                "data": original, "message": req.message, "document_text": req.document_text,
                "document_name": req.document_name, "action": req.action,
            }
            try:
                async for chunk in graph.astream(state, stream_mode="updates"):
                    for node, upd in chunk.items():
                        state.update(upd)
                        yield sse("node", {"node": node, "label": NODE_LABELS.get(node, node)})
                        if "data" in upd:
                            yield sse("state", {"data": upd["data"]})
                final = validated(state["data"])
                tool = state.get("intent")
                if final != original:
                    snapshot(db, inv, f"{tool}: {user_text[:80]}")
                    inv.version += 1
                    source = "document" if req.document_text else "chat"
                    changed = write_audit(db, inv, original, final, source=source, actor="ai", tool=tool)
                    inv.data = final
                    inv.title = derive_title(final)
                    inv.status = "draft"
                else:
                    changed = []
                reply = state.get("reply", "Done.")
                db.add(Message(investigation_id=inv.id, role="user", content=user_text,
                               meta={"document": req.document_name} if req.document_name else {}))
                db.add(Message(investigation_id=inv.id, role="assistant", content=reply,
                               meta={"tool": tool, "changed": changed}))
                db.commit()
                yield sse("message", {"content": reply, "tool": tool, "changed": changed})
                yield sse("done", {"version": inv.version, "title": inv.title})
            except Exception as e:  # surface model/validation failures to the UI instead of hanging
                db.rollback()
                traceback.print_exc()
                yield sse("error", {"detail": f"{type(e).__name__}: {str(e)[:300]}"})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
