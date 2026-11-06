"""Pydantic models: the investigation document + the structured outputs the LLM must produce."""
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _one_id(prefix: str):
    """Models sometimes answer 'H1 (Method)', ['H1','H2'] or null; normalise to a single clean id or None."""
    def clean(v):
        if isinstance(v, (list, tuple)):
            v = v[0] if v else None
        if isinstance(v, str):
            m = re.search(rf"{prefix}\d+", v)
            return m.group(0) if m else None
        return v
    return clean


def _id_list(prefix: str):
    def clean(v):
        if isinstance(v, str):
            v = [v]
        out = []
        for item in v or []:
            m = re.search(rf"{prefix}\d+", str(item))
            if m and m.group(0) not in out:
                out.append(m.group(0))
        return out
    return clean

Category = Literal["Man", "Machine", "Material", "Method", "Measurement", "Environment"]
Confidence = Literal["low", "medium", "high"]
HypothesisStatus = Literal["suggested", "supported", "confirmed", "rejected"]
Source = Literal["document", "chat", "ai_inference", "user"]


# ---------- investigation document (stored as JSONB) ----------

class Deviation(BaseModel):
    deviation_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    deviation_type: Optional[str] = None  # e.g. OOS, OOT, process excursion, equipment failure, contamination
    classification: Optional[str] = None  # Critical / Major / Minor (AI-suggested, QA to confirm)
    date_detected: Optional[str] = None
    detected_by: Optional[str] = None
    department: Optional[str] = None
    immediate_actions: Optional[str] = None
    impact_assessment: Optional[str] = None


class BatchContext(BaseModel):
    product_name: Optional[str] = None
    grade_or_spec: Optional[str] = None
    batch_number: Optional[str] = None
    process_stage: Optional[str] = None
    equipment_ids: Optional[str] = None
    raw_material_lots: Optional[str] = None
    batch_size: Optional[str] = None
    affected_quantity: Optional[str] = None
    manufacturing_date: Optional[str] = None
    test_result: Optional[str] = None  # e.g. "IPA 5800 ppm vs limit NMT 5000 ppm"


class WhyStep(BaseModel):
    level: int
    question: str
    answer: str
    evidence_refs: list[str] = Field(default_factory=list)
    critic_note: Optional[str] = None  # set when the critic pushed the chain deeper

    _refs = field_validator("evidence_refs", mode="before")(_id_list("E"))


class Hypothesis(BaseModel):
    id: str
    category: Category
    statement: str
    rationale: Optional[str] = None
    confidence: Confidence = "low"
    status: HypothesisStatus = "suggested"
    evidence_for: list[str] = Field(default_factory=list)  # evidence ids
    evidence_against: list[str] = Field(default_factory=list)
    confirmed_by: Optional[str] = None

    _ev = field_validator("evidence_for", "evidence_against", mode="before")(_id_list("E"))


class EvidenceItem(BaseModel):
    id: str
    description: str
    kind: Literal["record", "test_result", "observation", "statement", "document"] = "observation"
    source: Source = "document"
    quote: Optional[str] = None  # verbatim snippet it came from, if any


class Gap(BaseModel):
    id: str
    item: str  # what is missing
    why_needed: str
    priority: Literal["high", "medium", "low"] = "medium"
    related_hypothesis: Optional[str] = None
    resolved: bool = False

    _hid = field_validator("related_hypothesis", mode="before")(_one_id("H"))


class Capa(BaseModel):
    id: str
    type: Literal["Correction", "Corrective", "Preventive"]
    action: str
    linked_hypothesis: Optional[str] = None
    rationale: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    effectiveness_check: Optional[str] = None
    accepted: bool = False

    _hid = field_validator("linked_hypothesis", mode="before")(_one_id("H"))


class Health(BaseModel):
    evidence_sufficiency: int = 0  # 0-100
    readiness: Literal["not_ready", "needs_evidence", "ready_for_review"] = "not_ready"
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    source: Source
    quote: Optional[str] = None
    accepted: bool = False  # AI-sourced values stay "suggested" until a person accepts


class InvestigationData(BaseModel):
    deviation: Deviation = Field(default_factory=Deviation)
    batch: BatchContext = Field(default_factory=BatchContext)
    why_chain: list[WhyStep] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    capa: list[Capa] = Field(default_factory=list)
    health: Health = Field(default_factory=Health)
    provenance: dict[str, Provenance] = Field(default_factory=dict)


# ---------- structured LLM outputs ----------

class ExtractedEvidence(BaseModel):
    """Lenient shape for model output; converted to EvidenceItem (with a real id) after validation."""
    description: Optional[str] = None
    kind: str = "observation"
    quote: Optional[str] = None


class Extraction(BaseModel):
    """Output of the ingest tool: form fields + evidence items found in the source text."""
    deviation: Deviation
    batch: BatchContext
    evidence: list[ExtractedEvidence] = Field(default_factory=list)
    quotes: dict[str, str] = Field(default_factory=dict, description="field path -> verbatim supporting snippet")


class NewEvidence(BaseModel):
    description: str
    kind: str = "statement"


class FieldUpdate(BaseModel):
    path: str = Field(description="dotted path, e.g. batch.batch_number or deviation.classification")
    value: Any


class EditPlan(BaseModel):
    """Output of the edit tool: ONLY the fields the user mentioned."""
    field_updates: list[FieldUpdate] = Field(default_factory=list)
    new_evidence: list[NewEvidence] = Field(default_factory=list)
    resolves_gaps: list[str] = Field(default_factory=list)  # ids of open evidence gaps this message answers
    reply: str = ""

    _gids = field_validator("resolves_gaps", mode="before")(_id_list("G"))


class IntentOut(BaseModel):
    intent: Literal["ingest", "edit", "analyze", "challenge", "question"]


class HypothesizeOut(BaseModel):
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    why_chain: list[WhyStep] = Field(default_factory=list)


class GapsCapaOut(BaseModel):
    """One call produces both the missing-evidence list and the CAPA plan (saves tokens)."""
    gaps: list[Gap] = Field(default_factory=list)
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)
    capa: list[Capa] = Field(default_factory=list)


class AnswerOut(BaseModel):
    reply: str


class CriticVerdict(BaseModel):
    shallow: bool = Field(description="True if the chain stops at human error / training / 'not followed'")
    critique: str = ""
    deeper_steps: list[WhyStep] = Field(default_factory=list, description="replacement/extension of the chain")
    warnings: list[str] = Field(default_factory=list)


# ---------- API payloads ----------

class ChatRequest(BaseModel):
    message: str = ""
    document_text: Optional[str] = None
    document_name: Optional[str] = None
    action: Optional[Literal["analyze", "challenge", "gaps", "capa"]] = None


class ManualFieldEdit(BaseModel):
    path: str
    value: Any


class ConfirmRequest(BaseModel):
    confirmed_by: str
