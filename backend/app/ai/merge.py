"""Deterministic helpers that keep AI output safe: id handling, field setting with provenance,
guardrails on hypothesis status, and the (non-LLM) evidence-sufficiency score."""
import json

from ..schemas import BatchContext, Deviation, Health, InvestigationData, Provenance

DEVIATION_FIELDS = set(Deviation.model_fields)
BATCH_FIELDS = set(BatchContext.model_fields)


def valid_path(path: str) -> bool:
    parts = path.split(".")
    if len(parts) != 2:
        return False
    scope, key = parts
    return (scope == "deviation" and key in DEVIATION_FIELDS) or (scope == "batch" and key in BATCH_FIELDS)


def get_field(d: InvestigationData, path: str):
    scope, key = path.split(".")
    return getattr(getattr(d, scope), key)


def set_field(d: InvestigationData, path: str, value, *, source: str, quote: str | None = None,
              accepted: bool = False, force: bool = False) -> bool:
    """Set a scalar field. Without `force`, never overwrite a value a person already accepted."""
    if not valid_path(path):
        return False
    prov = d.provenance.get(path)
    if prov and prov.accepted and not force:
        return False
    scope, key = path.split(".")
    setattr(getattr(d, scope), key, None if value is None else str(value))
    d.provenance[path] = Provenance(source=source, quote=quote, accepted=accepted)
    return True


def next_id(prefix: str, existing: list[str]) -> str:
    nums = [int(x[len(prefix):]) for x in existing if x.startswith(prefix) and x[len(prefix):].isdigit()]
    return f"{prefix}{(max(nums) + 1) if nums else 1}"


def _dump(obj, exclude_none=True):
    return obj.model_dump(exclude_none=exclude_none)


def compact(d: InvestigationData, parts: tuple[str, ...] | None = None) -> str:
    """Investigation JSON for prompts. Groq's free tier is 8k tokens/min, so each stage gets only what it needs:
    nulls, provenance and health are always dropped; `parts` selects sections."""
    out: dict = {}
    want = set(parts or ("deviation", "batch", "evidence", "hypotheses", "why_chain", "gaps", "capa"))
    if "deviation" in want:
        out["deviation"] = _dump(d.deviation)
    if "batch" in want:
        out["batch"] = _dump(d.batch)
    if "evidence" in want:
        out["evidence"] = [{"id": e.id, "description": e.description} for e in d.evidence]
    if "hypotheses" in want:
        out["hypotheses"] = [h.model_dump(exclude_none=True, exclude={"rationale"}) for h in d.hypotheses]
    if "why_chain" in want:
        out["why_chain"] = [{"level": s.level, "answer": s.answer} for s in d.why_chain]
    if "gaps" in want:
        out["gaps"] = [{"id": g.id, "item": g.item, "resolved": g.resolved} for g in d.gaps]
    if "capa" in want:
        out["capa"] = [{"id": c.id, "type": c.type, "action": c.action, "accepted": c.accepted} for c in d.capa if c.accepted]
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def sanitize(d: InvestigationData) -> None:
    """Enforce guardrails no matter what the model said."""
    ev_ids = {e.id for e in d.evidence}
    hyp_ids = {h.id for h in d.hypotheses}
    for h in d.hypotheses:
        h.evidence_for = [i for i in h.evidence_for if i in ev_ids]
        h.evidence_against = [i for i in h.evidence_against if i in ev_ids]
        if h.status == "confirmed" and h.confirmed_by:
            continue  # a person signed this off; leave it alone
        if h.status == "rejected":
            continue  # a person rejected it
        # AI-assignable statuses are derived in code, not trusted from the model:
        # "supported" = more evidence for than against; otherwise it stays a suggestion. The AI can never confirm.
        h.status = "supported" if len(h.evidence_for) > len(h.evidence_against) else "suggested"
        h.confirmed_by = None
    for s in d.why_chain:
        s.evidence_refs = [i for i in s.evidence_refs if i in ev_ids]
    for g in d.gaps:
        if g.related_hypothesis not in hyp_ids:
            g.related_hypothesis = None
    for c in d.capa:
        if c.linked_hypothesis not in hyp_ids:
            c.linked_hypothesis = None


def recompute_health(d: InvestigationData, summary: str | None = None) -> None:
    """Evidence sufficiency is computed in code, not by the LLM, so it is explainable and stable."""
    ev_score = min(len(d.evidence), 8) / 8 * 40
    live = [h for h in d.hypotheses if h.status != "rejected"]
    coverage = (sum(1 for h in live if h.evidence_for) / len(live)) if live else 0
    high = [g for g in d.gaps if g.priority == "high"]
    open_high = sum(not g.resolved for g in high)
    gap_score = (1 - open_high / len(high)) if high else (1 if d.gaps else 0)
    score = round(ev_score + 30 * coverage + 30 * gap_score)
    confirmed = any(h.status == "confirmed" for h in d.hypotheses)
    if score >= 75 and open_high == 0 and confirmed:
        readiness = "ready_for_review"
    elif score < 35 and not d.hypotheses:
        readiness = "not_ready"
    else:
        readiness = "needs_evidence"
    open_total = sum(not g.resolved for g in d.gaps)
    d.health = Health(
        evidence_sufficiency=min(score, 100),
        readiness=readiness,
        summary=summary or (f"{open_total} evidence item(s) still open." if d.gaps else "Run analysis to assess evidence."),
        warnings=d.health.warnings,
    )
