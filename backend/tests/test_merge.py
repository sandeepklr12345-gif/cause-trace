"""Guardrail tests: the AI must never confirm a hypothesis, overwrite accepted values, or invent ids."""
from app.ai import merge
from app.schemas import Capa, EvidenceItem, Gap, Hypothesis, InvestigationData, WhyStep


def _data(**kw) -> InvestigationData:
    return InvestigationData(**kw)


def _ev(*ids: str) -> list[EvidenceItem]:
    return [EvidenceItem(id=i, description=f"evidence {i}") for i in ids]


def _hyp(hid: str, **kw) -> Hypothesis:
    return Hypothesis(id=hid, category="Method", statement=f"cause {hid}", **kw)


# ---------- paths and ids ----------

def test_valid_path_accepts_known_fields_only():
    assert merge.valid_path("deviation.title")
    assert merge.valid_path("batch.batch_number")
    assert not merge.valid_path("batch.nope")
    assert not merge.valid_path("health.summary")
    assert not merge.valid_path("deviation")


def test_next_id_continues_the_sequence():
    assert merge.next_id("E", []) == "E1"
    assert merge.next_id("E", ["E1", "E2", "E7"]) == "E8"
    assert merge.next_id("H", ["E3", "Hx"]) == "H1"


# ---------- set_field ----------

def test_set_field_records_provenance():
    d = _data()
    assert merge.set_field(d, "batch.batch_number", 1234, source="document", quote="Batch 1234")
    assert d.batch.batch_number == "1234"
    assert d.provenance["batch.batch_number"].source == "document"
    assert d.provenance["batch.batch_number"].accepted is False


def test_set_field_rejects_unknown_path():
    d = _data()
    assert merge.set_field(d, "batch.unknown", "x", source="chat") is False
    assert d.provenance == {}


def test_set_field_does_not_overwrite_accepted_value_unless_forced():
    d = _data()
    merge.set_field(d, "deviation.title", "Original", source="user", accepted=True)
    assert merge.set_field(d, "deviation.title", "AI rewrite", source="ai_inference") is False
    assert d.deviation.title == "Original"
    assert merge.set_field(d, "deviation.title", "User edit", source="user", accepted=True, force=True)
    assert d.deviation.title == "User edit"


# ---------- sanitize ----------

def test_sanitize_drops_references_to_missing_evidence():
    d = _data(
        evidence=_ev("E1"),
        hypotheses=[_hyp("H1", evidence_for=["E1", "E9"], evidence_against=["E8"])],
        why_chain=[WhyStep(level=1, question="why?", answer="because", evidence_refs=["E1", "E5"])],
    )
    merge.sanitize(d)
    assert d.hypotheses[0].evidence_for == ["E1"]
    assert d.hypotheses[0].evidence_against == []
    assert d.why_chain[0].evidence_refs == ["E1"]


def test_sanitize_derives_status_from_evidence_balance():
    d = _data(
        evidence=_ev("E1", "E2"),
        hypotheses=[
            _hyp("H1", evidence_for=["E1", "E2"], evidence_against=["E2"]),
            _hyp("H2", evidence_for=["E1"], evidence_against=["E1", "E2"], status="supported"),
        ],
    )
    merge.sanitize(d)
    assert d.hypotheses[0].status == "supported"
    assert d.hypotheses[1].status == "suggested"


def test_sanitize_ai_can_never_confirm_a_hypothesis():
    d = _data(evidence=_ev("E1"), hypotheses=[_hyp("H1", evidence_for=["E1"], status="confirmed")])
    merge.sanitize(d)  # status is "confirmed" but nobody signed it off
    assert d.hypotheses[0].status == "supported"
    assert d.hypotheses[0].confirmed_by is None


def test_sanitize_keeps_human_decisions():
    d = _data(hypotheses=[
        _hyp("H1", status="confirmed", confirmed_by="QA Lead"),
        _hyp("H2", status="rejected"),
    ])
    merge.sanitize(d)
    assert d.hypotheses[0].status == "confirmed"
    assert d.hypotheses[0].confirmed_by == "QA Lead"
    assert d.hypotheses[1].status == "rejected"


def test_sanitize_unlinks_unknown_hypotheses_from_gaps_and_capa():
    d = _data(
        hypotheses=[_hyp("H1")],
        gaps=[Gap(id="G1", item="x", why_needed="y", related_hypothesis="H1"),
              Gap(id="G2", item="x", why_needed="y", related_hypothesis="H9")],
        capa=[Capa(id="C1", type="Corrective", action="a", rationale="r", linked_hypothesis="H9")],
    )
    merge.sanitize(d)
    assert d.gaps[0].related_hypothesis == "H1"
    assert d.gaps[1].related_hypothesis is None
    assert d.capa[0].linked_hypothesis is None


# ---------- health score ----------

def test_health_of_empty_investigation_is_not_ready():
    d = _data()
    merge.recompute_health(d)
    assert d.health.evidence_sufficiency == 0
    assert d.health.readiness == "not_ready"


def test_health_needs_evidence_when_high_priority_gap_is_open():
    d = _data(
        evidence=_ev(*[f"E{i}" for i in range(1, 9)]),
        hypotheses=[_hyp("H1", evidence_for=["E1"], status="confirmed", confirmed_by="QA")],
        gaps=[Gap(id="G1", item="x", why_needed="y", priority="high")],
    )
    merge.recompute_health(d)
    assert d.health.readiness == "needs_evidence"
    assert "1 evidence item(s) still open" in d.health.summary


def test_health_ready_for_review_needs_confirmation_and_no_open_high_gaps():
    d = _data(
        evidence=_ev(*[f"E{i}" for i in range(1, 9)]),
        hypotheses=[_hyp("H1", evidence_for=["E1"], status="confirmed", confirmed_by="QA")],
        gaps=[Gap(id="G1", item="x", why_needed="y", priority="high", resolved=True)],
    )
    merge.recompute_health(d)
    assert d.health.evidence_sufficiency == 100
    assert d.health.readiness == "ready_for_review"


def test_health_score_never_exceeds_100():
    d = _data(evidence=_ev(*[f"E{i}" for i in range(1, 30)]))
    merge.recompute_health(d)
    assert d.health.evidence_sufficiency <= 100


# ---------- compact prompt JSON ----------

def test_compact_drops_nulls_and_selects_sections():
    d = _data(evidence=_ev("E1"))
    d.deviation.title = "OOS result"
    out = merge.compact(d, parts=("deviation", "evidence"))
    assert '"title":"OOS result"' in out
    assert "null" not in out
    assert '"batch"' not in out
    assert '"id":"E1"' in out
