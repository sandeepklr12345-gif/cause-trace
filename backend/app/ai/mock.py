"""Deterministic stand-in for the LLM so the whole flow (graph, SSE, UI) can be tested without a Groq key.

It is intentionally simple: label scanning + keyword rules, tuned to the sample
residual-solvent deviation. The real path (llm.py -> Groq) never touches this file.
"""
import re

from ..schemas import (
    AnswerOut, CriticVerdict, EditPlan, ExtractedEvidence, Extraction, Gap, GapsCapaOut, NewEvidence,
    Hypothesis, HypothesizeOut, IntentOut, WhyStep, Capa, Deviation, BatchContext,
)

LABELS = {
    "deviation no": "deviation.deviation_id", "deviation id": "deviation.deviation_id",
    "title": "deviation.title", "description": "deviation.description",
    "deviation type": "deviation.deviation_type", "date detected": "deviation.date_detected",
    "detected by": "deviation.detected_by", "department": "deviation.department",
    "immediate action": "deviation.immediate_actions", "immediate actions": "deviation.immediate_actions",
    "product": "batch.product_name", "grade": "batch.grade_or_spec", "batch no": "batch.batch_number",
    "batch number": "batch.batch_number", "process stage": "batch.process_stage", "stage": "batch.process_stage",
    "equipment": "batch.equipment_ids", "raw material lots": "batch.raw_material_lots",
    "batch size": "batch.batch_size", "affected quantity": "batch.affected_quantity",
    "manufacturing date": "batch.manufacturing_date", "test result": "batch.test_result",
}


def _scan(text: str):
    """Label/bullet scanner; wrapped continuation lines (typical of PDF text) are joined to the previous item."""
    fields, evidence = {}, []
    current = None  # ("field", path) | ("bullet", index)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([A-Za-z ./]{3,30}):\s*(.+)$", line)
        if m and m.group(1).strip().lower() in LABELS:
            path = LABELS[m.group(1).strip().lower()]
            fields[path] = m.group(2).strip()
            current = ("field", path)
        elif line.startswith(("- ", "• ", "* ")):
            evidence.append(line[2:].strip())
            current = ("bullet", len(evidence) - 1)
        elif line.endswith(":") and len(line) < 40:
            key = line[:-1].strip().lower()
            if key in LABELS:  # section header like "Description:" -> the value follows on the next lines
                path = LABELS[key]
                fields[path] = ""
                current = ("field", path)
            else:
                current = None
        elif current:
            kind, ref = current
            if kind == "field":
                fields[ref] = (fields[ref] + " " + line).strip()
            else:
                evidence[ref] += " " + line
    return fields, evidence


def _extraction(user: str, ctx: dict) -> Extraction:
    text = ctx.get("text", "")
    fields, bullets = _scan(text)
    dev, batch = {}, {}
    for path, value in fields.items():
        scope, key = path.split(".")
        (dev if scope == "deviation" else batch)[key] = value
    if not dev.get("description"):
        dev["description"] = text.strip()[:600]
    if "OOS" in text or "out of specification" in text.lower():
        dev.setdefault("deviation_type", "Out of Specification (OOS)")
    dev["classification"] = "Major"
    dev["impact_assessment"] = "Potential impact on batch disposition and any downstream batches using this API lot; patient risk to be assessed by QA."
    evidence = [ExtractedEvidence(description=b, kind="observation", quote=b) for b in bullets]
    quotes = {p: v for p, v in fields.items()}
    return Extraction(deviation=Deviation(**dev), batch=BatchContext(**batch), evidence=evidence, quotes=quotes)


def _match(evidence: list[dict], *keywords: str) -> list[str]:
    return [e["id"] for e in evidence if any(k in e["description"].lower() for k in keywords)]


def _hypothesize(ctx: dict) -> HypothesizeOut:
    ev = ctx["data"]["evidence"]
    existing = {h["id"]: h for h in ctx["data"]["hypotheses"]}
    spec = [
        ("H1", "Machine", "Vacuum degraded during drying (pump performance), leaving solvent in the cake.",
         ("vacuum", "mbar", "pump")),
        ("H2", "Method", "Drying end-point is defined by LOD only, which does not measure isopropanol, so the cycle was stopped early.",
         ("lod", "end-point", "terminated", "9 h", "9h")),
        ("H3", "Method", "Tray loading / bed depth exceeded the validated range, slowing solvent removal.",
         ("bed", "tray", "loading")),
        ("H4", "Measurement", "GC head-space result is analytically invalid (system suitability / calibration).",
         ("gc", "suitability", "calibration")),
    ]
    hyps = []
    for hid, cat, stmt, kws in spec:
        ids = _match(ev, *kws)
        if hid in existing and existing[hid]["status"] in ("confirmed",):
            hyps.append(Hypothesis(**existing[hid]))
            continue
        against = []
        if hid == "H4":  # a passed system-suitability check argues AGAINST an analytical cause
            against, ids = _match(ev, "suitability passed"), []
        hyps.append(Hypothesis(
            id=hid, category=cat, statement=stmt,
            rationale="Evidence in the record is consistent with this mechanism." if ids else "Plausible from process knowledge; no direct evidence yet.",
            confidence="medium" if len(ids) >= 1 else "low",
            status="supported" if ids else "suggested", evidence_for=ids,
            evidence_against=against,
        ))
    chain = [
        WhyStep(level=1, question="Why was the batch OOS for isopropanol?", answer="Residual isopropanol remained in the dried API."),
        WhyStep(level=2, question="Why did solvent remain after drying?", answer="The drying cycle ended before the solvent was fully removed."),
        WhyStep(level=3, question="Why did the cycle end early?", answer="The operator stopped the cycle at 9 h instead of the 12 h scheduled."),
        WhyStep(level=4, question="Why did the operator stop it?", answer="The operator did not follow the 12 h drying instruction."),
    ]
    return HypothesizeOut(hypotheses=hyps, why_chain=chain)


def _critic(ctx: dict) -> CriticVerdict:
    chain = ctx["data"]["why_chain"]
    last = (chain[-1]["answer"] if chain else "").lower()
    if not chain or not re.search(r"operator|did not follow|training|human|negligen|careless", last):
        return CriticVerdict(shallow=False, critique="Chain ends at a system-level cause.")
    deeper = [
        WhyStep(level=1, question="Why was the batch OOS for isopropanol?", answer="Residual isopropanol remained in the dried API."),
        WhyStep(level=2, question="Why did solvent remain after drying?", answer="The cycle ended before solvent removal was complete, with vacuum below target during part of the cycle."),
        WhyStep(level=3, question="Why was the cycle ended at 9 h?", answer="The in-process LOD result met its limit, and the SOP allows release of the cycle on LOD alone."),
        WhyStep(level=4, question="Why does the SOP allow that?", answer="End-point was defined on LOD only; LOD does not detect isopropanol and no residual-solvent in-process check exists.", critic_note="Pushed past 'operator did not follow the instruction'."),
        WhyStep(level=5, question="Why was low vacuum not caught during the cycle?", answer="The vacuum alarm is set at 300 mbar versus a 50 mbar target, and the pump preventive maintenance was overdue.", critic_note="System-level control gap."),
    ]
    return CriticVerdict(
        shallow=True,
        critique="'Operator did not follow instruction' is a symptom, not a root cause. Regulators expect the system conditions that allowed it.",
        deeper_steps=deeper,
        warnings=["Human error alone is not accepted as a root cause; chain was extended to system causes."],
    )


GAP_SPEC = [
    ("G1", "Dryer vacuum trend / audit trail for the cycle", "Confirms or rules out vacuum loss (H1).", "high", "H1", ("vacuum trend", "audit trail", "vacuum log", "vacuum dropped", "vacuum rose")),
    ("G2", "Vacuum pump preventive-maintenance and calibration records", "Shows whether PM was overdue.", "high", "H1", ("pm record", "maintenance record", "pm overdue", "maintenance was")),
    ("G3", "Vacuum alarm set-points and interlock configuration", "Explains why a vacuum excursion did not trigger action.", "high", "H1", ("alarm set", "alarm configuration", "alarm is set")),
    ("G4", "Tray loading record and validated bed-depth range", "Tests whether loading exceeded validated range (H3).", "medium", "H3", ("loading record", "bed depth was", "bed depth of")),
    ("G5", "GC-HS system suitability and calibration data", "Rules in/out an analytical cause (H4).", "medium", "H4", ("system suitability",)),
    ("G6", "Drying SOP revision history and validation basis for LOD end-point", "Needed to evidence the method cause (H2).", "medium", "H2", ("sop revision", "validation basis")),
]


def _gaps(ctx: dict) -> GapsCapaOut:
    blob = " ".join(e["description"].lower() for e in ctx["data"]["evidence"])
    gaps = []
    for gid, item, why, prio, hid, kws in GAP_SPEC:
        gaps.append(Gap(id=gid, item=item, why_needed=why, priority=prio, related_hypothesis=hid,
                        resolved=any(k in blob for k in kws)))
    open_n = sum(not g.resolved for g in gaps)
    return GapsCapaOut(gaps=gaps, summary=f"{open_n} evidence item(s) still needed before the root cause can be confirmed.",
                       warnings=["No hypothesis is confirmed; AI conclusions are suggestions until a qualified person signs off."],
                       capa=_capa(ctx))


def _capa(ctx: dict) -> list[Capa]:
    items = [
        Capa(id="C1", type="Correction", action="Keep the batch in quarantine; evaluate re-drying under an approved reprocessing protocol and retest residual solvents before disposition.",
             linked_hypothesis="H2", rationale="Contains the immediate product-quality risk without pre-judging the cause.",
             effectiveness_check="Retest isopropanol by GC-HS meets NMT 5,000 ppm."),
        Capa(id="C2", type="Corrective", action="Inspect, repair and requalify vacuum pump VP-204; complete overdue PM.",
             linked_hypothesis="H1", rationale="Removes the most likely equipment cause if the vacuum trend confirms it.",
             effectiveness_check="Vacuum reaches <=50 mbar within 30 min on 3 consecutive cycles."),
        Capa(id="C3", type="Corrective", action="Revise the drying SOP: end-point = LOD plus an in-process residual-solvent check; minimum drying time retained.",
             linked_hypothesis="H2", rationale="LOD cannot detect isopropanol, so it cannot be the sole release criterion for the cycle.",
             effectiveness_check="No residual-solvent OOS in the next 10 batches."),
        Capa(id="C4", type="Preventive", action="Tighten vacuum alarm to 100 mbar with a hold/interlock, and apply to all tray dryers of the same design.",
             linked_hypothesis="H1", rationale="Prevents the same failure on other dryers and products.",
             effectiveness_check="Alarm challenge test passed; zero uncaught excursions in 6 months."),
        Capa(id="C5", type="Preventive", action="Add overdue-PM escalation to the maintenance system so equipment cannot be used past due date.",
             linked_hypothesis="H1", rationale="Addresses the systemic reason PM can lapse unnoticed.",
             effectiveness_check="Quarterly report shows 0 equipment used past PM due date."),
    ]
    return items


def _edit(user: str) -> EditPlan:
    updates, evidence, notes = [], [], []
    m = re.search(r"batch(?: number| no\.?)?\s*(?:is|=|:)\s*([A-Za-z0-9\-]{4,})", user, re.I)
    if m:
        updates.append({"path": "batch.batch_number", "value": m.group(1)})
        notes.append(f"batch number → {m.group(1)}")
    m = re.search(r"quantity\s*(?:is|=|:)\s*(\d[\d,\.]*\s*[A-Za-z]+(?:\s*\([^)]*\))?)", user, re.I)
    if m:
        updates.append({"path": "batch.affected_quantity", "value": m.group(1).strip()})
        notes.append(f"affected quantity → {m.group(1).strip()}")
    if re.search(r"vacuum|log shows|trend|maintenance|\bpm\b|alarm|bed depth|loading", user, re.I):
        evidence.append(NewEvidence(description=user.strip().rstrip("."), kind="statement"))
        notes.append("recorded your statement as evidence")
    reply = ("Done: " + "; ".join(notes) + ". Everything else is unchanged.") if notes else "I couldn't find a specific field to change in that message."
    return EditPlan(field_updates=updates, new_evidence=evidence, reply=reply)


def _intent(user: str, ctx: dict) -> IntentOut:
    u = user.lower()
    if re.search(r"challenge|devil|are you sure|push back", u):
        return IntentOut(intent="challenge")
    if re.search(r"analy[sz]e|root cause|5 whys|fishbone|capa|what's missing|what is missing", u):
        return IntentOut(intent="analyze")
    if "?" in u and not re.search(r"\bis\b.*\d", u):
        return IntentOut(intent="question")
    return IntentOut(intent="edit")


def respond(schema, ctx: dict):
    name = schema.__name__
    if name == "Extraction":
        return _extraction(ctx.get("user", ""), ctx)
    if name == "EditPlan":
        return _edit(ctx.get("user", ""))
    if name == "IntentOut":
        return _intent(ctx.get("user", ""), ctx)
    if name == "HypothesizeOut":
        return _hypothesize(ctx)
    if name == "CriticVerdict":
        return _critic(ctx)
    if name == "GapsCapaOut":
        return _gaps(ctx)
    if name == "AnswerOut":
        return AnswerOut(reply="This is mock mode, so I can't answer open questions. Add a Groq key to enable full answers. You can still run Analyze or Challenge.")
    raise ValueError(f"no mock for {name}")
