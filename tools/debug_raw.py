"""Print raw structured outputs for the sample PDF to debug prompt/schema issues (real Groq)."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ai import prompts  # noqa: E402
from app.ai.llm import structured_call  # noqa: E402
from app.schemas import Extraction, GapsCapaOut, InvestigationData  # noqa: E402
from app.ai.merge import compact  # noqa: E402
from app.services.documents import extract_text  # noqa: E402

PDF = ROOT / "samples" / "DEV-2026-0412_residual_solvent.pdf"


async def main():
    text, _ = extract_text(PDF.name, PDF.read_bytes())
    print("--- PDF TEXT (first 700 chars)\n", text[:700])
    out = await structured_call(Extraction, prompts.INGEST, f"SOURCE TEXT:\n{text}", tier="alt")
    print("\n--- deviation:", out.deviation.model_dump_json(exclude_none=True))
    print("--- quotes:", json.dumps(out.quotes)[:400])
    d = InvestigationData()
    d.evidence = []
    hyps = [{"id": "H1", "category": "Machine", "statement": "Vacuum degraded during drying", "confidence": "low", "status": "suggested"},
            {"id": "H2", "category": "Method", "statement": "LOD-only end-point stopped the cycle early", "confidence": "medium", "status": "supported", "evidence_for": ["E1"]}]
    ev = [{"id": "E1", "description": "Operator ended drying at 9 h of 12 h after LOD 0.4%"},
          {"id": "E2", "description": "The dryer log shows vacuum rose to 300 mbar after 3 hours."}]
    ctx = json.dumps({"batch": {"product_name": "Atorvastatin API"}, "evidence": ev, "hypotheses": hyps, "gaps": [], "capa": []})
    raw = await structured_call(GapsCapaOut, prompts.PLAN + "\nINVESTIGATION:\n" + ctx, "List missing evidence and recommend CAPA.", tier="heavy")
    print("\n--- gaps:", [(g.id, g.item[:50], g.related_hypothesis, g.resolved) for g in raw.gaps])
    print("--- capa links:", [(c.id, c.type, c.linked_hypothesis) for c in raw.capa])


asyncio.run(main())
