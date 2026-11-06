"""LangGraph nodes. Each takes the state, calls the LLM through structured_call, and returns a state patch."""
import json
from typing import TypedDict

from ..schemas import (
    AnswerOut, CriticVerdict, EditPlan, EvidenceItem, Extraction, GapsCapaOut,
    HypothesizeOut, IntentOut, InvestigationData, Provenance,
)
from . import prompts
from .llm import structured_call
from .merge import compact, next_id, recompute_health, sanitize, set_field, valid_path

INFERRED = {"deviation.classification", "deviation.impact_assessment", "deviation.deviation_type"}
IMPACT_FIELDS = {
    "batch.affected_quantity", "batch.batch_size", "batch.test_result", "batch.process_stage", "batch.equipment_ids",
    "batch.raw_material_lots", "deviation.description", "deviation.deviation_type", "deviation.classification",
    "deviation.impact_assessment",
}
EVIDENCE_KINDS = {"record", "test_result", "observation", "statement", "document"}


def _kind(k: str) -> str:
    return k if k in EVIDENCE_KINDS else "observation"


class State(TypedDict, total=False):
    data: dict
    message: str
    document_text: str | None
    document_name: str | None
    action: str | None
    intent: str
    reply: str
    reanalyze: bool


def _load(state: State) -> InvestigationData:
    return InvestigationData.model_validate(state["data"])


# ---------------------------------------------------------------- routing

async def route(state: State) -> dict:
    d = _load(state)
    action = state.get("action")
    if state.get("document_text"):
        intent = "ingest"
    elif action == "challenge":
        intent = "challenge"
    elif action in ("analyze", "gaps", "capa"):
        intent = "analyze"
    elif not d.deviation.description and not d.batch.product_name:
        intent = "ingest"  # nothing logged yet: treat the message as the incident report
    else:
        out = await structured_call(IntentOut, prompts.INTENT, state["message"], {"user": state["message"], "data": d.model_dump()}, tier="fast")
        # An investigation already exists: new facts/corrections typed in chat are edits, never a fresh intake.
        intent = "edit" if out.intent == "ingest" else out.intent
    return {"intent": intent}


def pick_branch(state: State) -> str:
    return {"ingest": "ingest", "edit": "edit", "analyze": "hypothesize",
            "challenge": "critic", "question": "answer"}[state["intent"]]


# ---------------------------------------------------------------- tool 1: ingest

async def ingest(state: State) -> dict:
    d = _load(state)
    text = state.get("document_text") or state["message"]
    from_doc = bool(state.get("document_text"))
    src = "document" if from_doc else "chat"
    out = await structured_call(
        Extraction, prompts.INGEST, f"SOURCE TEXT:\n{text}", {"text": text, "data": d.model_dump(), "user": text}, tier="alt"
    )
    filled = 0
    for scope in ("deviation", "batch"):
        for key, value in getattr(out, scope).model_dump().items():
            if value in (None, ""):
                continue
            path = f"{scope}.{key}"
            inferred = path in INFERRED and path not in out.quotes
            if set_field(d, path, value, source="ai_inference" if inferred else src, quote=out.quotes.get(path)):
                filled += 1
    known = {e.description.strip().lower() for e in d.evidence}
    added = 0
    for e in out.evidence:
        desc = (e.description or e.quote or "").strip()
        if not desc or desc.lower() in known:
            continue
        known.add(desc.lower())
        d.evidence.append(EvidenceItem(
            id=next_id("E", [x.id for x in d.evidence]), description=desc, kind=_kind(e.kind),
            source=src, quote=e.quote))  # type: ignore[arg-type]
        added += 1
    reply = (f"Read {state.get('document_name') or 'your message'}: filled {filled} form field(s) and "
             f"logged {added} piece(s) of evidence.")
    return {"data": d.model_dump(), "reply": reply}


# ---------------------------------------------------------------- tool 2: edit

async def edit(state: State) -> dict:
    d = _load(state)
    msg = state["message"]
    open_gaps = json.dumps([{"id": g.id, "item": g.item} for g in d.gaps if not g.resolved], ensure_ascii=False)
    plan = await structured_call(
        EditPlan,
        prompts.EDIT + "\nCURRENT FORM VALUES:\n" + compact(d, ("deviation", "batch")) + "\nOPEN GAPS:\n" + open_gaps,
        f"USER MESSAGE:\n{msg}", {"user": msg, "data": d.model_dump()}, tier="fast")
    gap_ids = {g.id for g in d.gaps if not g.resolved}
    for g in d.gaps:
        if g.id in plan.resolves_gaps and g.id in gap_ids:
            g.resolved = True
    applied, rejected = [], []
    for fu in plan.field_updates:
        if valid_path(fu.path) and set_field(d, fu.path, fu.value, source="chat", quote=msg[:200], accepted=True, force=True):
            applied.append(fu.path)
        else:
            rejected.append(fu.path)
    for e in plan.new_evidence:
        if e.description.strip():
            d.evidence.append(EvidenceItem(
                id=next_id("E", [x.id for x in d.evidence]), description=e.description.strip(),
                kind=_kind(e.kind), source="chat", quote=msg[:200]))
    reply = plan.reply or "Updated."
    if rejected:
        reply += f" (Ignored unknown field(s): {', '.join(rejected)}.)"
    # Re-run the analysis only when the change can alter it: new evidence or an impact-relevant field. A corrected
    # batch number alone doesn't change any cause, so skip three LLM calls (and the 8k tokens/min budget).
    reanalyze = bool(plan.new_evidence) or any(p in IMPACT_FIELDS for p in applied)
    return {"data": d.model_dump(), "reply": reply, "reanalyze": reanalyze}


def after_edit(state: State) -> str:
    return "hypothesize" if state.get("reanalyze") else "finalize"


# ---------------------------------------------------------------- tool 3: analyze

async def hypothesize(state: State) -> dict:
    d = _load(state)
    d.health.warnings = []
    out = await structured_call(HypothesizeOut, prompts.HYPOTHESIZE + "\nINVESTIGATION:\n" + compact(d, ("deviation", "batch", "evidence", "hypotheses")),
                                "Produce hypotheses and the 5 Whys chain.", {"data": d.model_dump()})
    old = {h.id: h for h in d.hypotheses}
    protected = {h.id: h for h in d.hypotheses if h.status in ("confirmed", "rejected")}
    merged = []
    for h in out.hypotheses:
        prev = old.get(h.id)
        if h.id in protected:
            h = protected[h.id]
        elif prev:
            # Evidence links are sticky: re-analysis can add links or argue against one, but cannot silently drop
            # support just because the model's answer varied between runs.
            h.evidence_for = [e for e in dict.fromkeys(prev.evidence_for + h.evidence_for) if e not in h.evidence_against]
            if (d.provenance.get(f"hypotheses.{h.id}") or Provenance(source="ai_inference")).source == "user":
                h.statement, h.category = prev.statement, prev.category  # a person reworded it; keep their wording
        merged.append(h)
    merged += [h for hid, h in protected.items() if hid not in {x.id for x in merged}]
    d.hypotheses = merged
    d.why_chain = out.why_chain
    sanitize(d)
    for h in d.hypotheses:
        d.provenance.setdefault(f"hypotheses.{h.id}", Provenance(source="ai_inference"))
    return {"data": d.model_dump()}


async def critic(state: State) -> dict:
    d = _load(state)
    verdict = await structured_call(CriticVerdict, prompts.CRITIC + "\nINVESTIGATION:\n" + compact(d, ("evidence", "hypotheses", "why_chain")),
                                    "Review the 5 Whys chain.", {"data": d.model_dump()}, tier="alt")  # separate model from the one that wrote the chain
    if verdict.shallow and verdict.deeper_steps:
        for i, s in enumerate(verdict.deeper_steps, 1):
            s.level = i
        d.why_chain = verdict.deeper_steps
    msgs = list(verdict.warnings)
    if verdict.critique and verdict.shallow:
        msgs.insert(0, verdict.critique)
    for w in msgs:
        if w not in d.health.warnings:
            d.health.warnings.append(w)
    sanitize(d)
    note = ("Challenge result: the chain ended at human error, so I pushed it to system-level causes."
            if verdict.shallow else "Challenge result: the chain already reaches a system-level cause.")
    return {"data": d.model_dump(), "reply": state.get("reply") or note}


async def plan(state: State) -> dict:
    """Gap radar + CAPA in one call (one prompt/one copy of the investigation: halves token use)."""
    d = _load(state)
    out = await structured_call(GapsCapaOut, prompts.PLAN + "\nINVESTIGATION:\n" + compact(d, ("batch", "evidence", "hypotheses", "gaps", "capa")),
                                "List missing evidence and recommend CAPA.", {"data": d.model_dump()}, tier="heavy")
    already_resolved = {g.id for g in d.gaps if g.resolved}  # closed by the user's own answers; the model can't reopen them
    d.gaps = out.gaps
    for g in d.gaps:
        if g.id in already_resolved:
            g.resolved = True
    kept = [c for c in d.capa if c.accepted]  # never overwrite CAPA a person already accepted
    kept_ids = {c.id for c in kept}
    d.capa = kept + [c for c in out.capa if c.id not in kept_ids]
    sanitize(d)
    for w in out.warnings:
        if w not in d.health.warnings:
            d.health.warnings.append(w)
    for g in d.gaps:
        d.provenance.setdefault(f"gaps.{g.id}", Provenance(source="ai_inference"))
    for c in d.capa:
        d.provenance.setdefault(f"capa.{c.id}", Provenance(source="ai_inference"))
    recompute_health(d, out.summary or None)
    return {"data": d.model_dump()}


async def answer(state: State) -> dict:
    d = _load(state)
    out = await structured_call(AnswerOut, prompts.ANSWER + "\nINVESTIGATION:\n" + compact(d),
                                state["message"], {"user": state["message"], "data": d.model_dump()}, tier="fast")
    return {"reply": out.reply}


async def finalize(state: State) -> dict:
    d = _load(state)
    recompute_health(d, d.health.summary or None)
    h = d.health
    open_gaps = [g.item for g in d.gaps if not g.resolved and g.priority == "high"][:3]
    bits = [state.get("reply") or ""]
    if state["intent"] != "question":
        bits.append(f"Evidence sufficiency is {h.evidence_sufficiency}%.")
        if open_gaps:
            bits.append("Still needed: " + "; ".join(open_gaps) + ".")
        bits.append("All causes are suggestions until a qualified person confirms them.")
    return {"data": d.model_dump(), "reply": " ".join(b for b in bits if b)}
