"""LLMs return messy ids; the schema validators must normalise them to clean ids."""
import pytest
from pydantic import ValidationError

from app.schemas import Capa, ChatRequest, EditPlan, Gap, Hypothesis


def _hyp(**kw) -> Hypothesis:
    return Hypothesis(id="H1", category="Machine", statement="s", **kw)


def test_evidence_ids_are_extracted_from_free_text():
    h = _hyp(evidence_for=["E1 (batch record)", "see E2", "E1"], evidence_against="E3")
    assert h.evidence_for == ["E1", "E2"]  # deduplicated, order kept
    assert h.evidence_against == ["E3"]


def test_non_id_strings_are_dropped():
    assert _hyp(evidence_for=["no id here"]).evidence_for == []


def test_single_hypothesis_id_is_normalised():
    gap = lambda v: Gap(id="G1", item="i", why_needed="w", related_hypothesis=v)  # noqa: E731
    assert gap("H2 (Method)").related_hypothesis == "H2"
    assert gap(["H3", "H4"]).related_hypothesis == "H3"
    assert gap("unknown").related_hypothesis is None
    assert gap(None).related_hypothesis is None


def test_capa_links_are_normalised():
    c = Capa(id="C1", type="Preventive", action="a", rationale="r", linked_hypothesis="H5.")
    assert c.linked_hypothesis == "H5"


def test_edit_plan_normalises_resolved_gap_ids():
    plan = EditPlan(resolves_gaps="G2 answered")
    assert plan.resolves_gaps == ["G2"]


def test_invalid_category_is_rejected():
    with pytest.raises(ValidationError):
        Hypothesis(id="H1", category="Weather", statement="s")


def test_chat_request_rejects_unknown_action():
    assert ChatRequest(action="analyze").action == "analyze"
    with pytest.raises(ValidationError):
        ChatRequest(action="delete_everything")
