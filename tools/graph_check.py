"""Run the LangGraph workflow directly (no server/DB) and print per-node timing + key outputs.

    backend\\.venv\\Scripts\\python.exe -I tools\\graph_check.py
"""
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.graph import graph  # noqa: E402
from app.config import settings  # noqa: E402
from app.schemas import InvestigationData  # noqa: E402
from app.services.documents import extract_text  # noqa: E402

PDF = ROOT / "samples" / "DEV-2026-0412_residual_solvent.pdf"


async def run(state: dict, label: str) -> dict:
    print(f"\n=== {label}")
    t0 = last = time.time()
    async for chunk in graph.astream(state, stream_mode="updates"):
        for node, upd in chunk.items():
            state.update(upd)
            now = time.time()
            print(f"  {node:<12} {now - last:5.1f}s")
            last = now
    print(f"  total {time.time() - t0:.1f}s | reply: {state.get('reply', '')[:300]}")
    return state


async def main():
    print("LLM:", "mock" if settings.use_mock else settings.groq_model)
    text, _ = extract_text(PDF.name, PDF.read_bytes())
    st = {"data": InvestigationData().model_dump(), "message": "", "document_text": text, "document_name": PDF.name, "action": None}
    st = await run(st, "INGEST pdf")
    d = InvestigationData.model_validate(st["data"])
    print("batch:", d.batch.product_name, "|", d.batch.batch_number, "|", d.batch.affected_quantity, "|", d.batch.test_result)
    print("deviation:", d.deviation.deviation_id, "|", d.deviation.title, "|", d.deviation.classification)
    print("evidence:", len(d.evidence), "| hypotheses:", [(h.id, h.category, h.status, h.evidence_for) for h in d.hypotheses])
    print("why chain:", [s.answer[:70] for s in d.why_chain])
    print("gaps:", [(g.id, g.priority, g.resolved) for g in d.gaps])
    print("capa:", [(c.id, c.type, c.linked_hypothesis) for c in d.capa])
    print("health:", d.health.evidence_sufficiency, d.health.readiness, d.health.warnings[:2])

    st.update(document_text=None, message="Sorry, the batch number is CHG260712A and affected quantity is 50 kg (2 HDPE drums)")
    st = await run(st, "EDIT")
    d2 = InvestigationData.model_validate(st["data"])
    print("batch now:", d2.batch.product_name, "|", d2.batch.batch_number, "|", d2.batch.affected_quantity)
    assert d2.batch.batch_number == "CHG260712A" and d2.batch.product_name == d.batch.product_name

    st.update(message="The dryer log shows vacuum rose to 300 mbar after 3 hours into the cycle.")
    st = await run(st, "EDIT with new evidence")
    d3 = InvestigationData.model_validate(st["data"])
    print("evidence:", len(d3.evidence), "| hypotheses:", [(h.id, h.status, h.evidence_for) for h in d3.hypotheses])
    print("gaps open:", [g.id for g in d3.gaps if not g.resolved], "| health:", d3.health.evidence_sufficiency)
    assert not any(h.status == "confirmed" for h in d3.hypotheses), "AI must never confirm"
    print("\nGRAPH CHECK OK")


asyncio.run(main())
