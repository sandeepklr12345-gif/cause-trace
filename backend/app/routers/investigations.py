"""REST endpoints for the investigation record: CRUD, human review actions, save, undo."""
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.merge import recompute_health, sanitize, set_field, valid_path
from ..db import get_db
from ..models import AuditEntry, Investigation, Message, Snapshot
from ..schemas import ConfirmRequest, InvestigationData, ManualFieldEdit, Provenance
from ..services.documents import extract_text
from ..services.persist import derive_title, snapshot, write_audit

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


def get_inv(db: Session, inv_id: int) -> Investigation:
    inv = db.get(Investigation, inv_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    return inv


def serialize(inv: Investigation, db: Session) -> dict:
    msgs = db.scalars(select(Message).where(Message.investigation_id == inv.id).order_by(Message.id)).all()
    return {
        "id": inv.id, "title": inv.title, "status": inv.status, "version": inv.version,
        "data": inv.data,
        "messages": [{"role": m.role, "content": m.content, "meta": m.meta} for m in msgs],
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def commit_change(db: Session, inv: Investigation, d: InvestigationData, *, source: str, actor: str, label: str) -> None:
    """Persist a human edit: snapshot, audit, bump version."""
    old = inv.data
    snapshot(db, inv, label)
    sanitize(d)
    recompute_health(d, d.health.summary or None)
    new = d.model_dump()
    inv.version += 1
    write_audit(db, inv, old, new, source=source, actor=actor, tool=None)
    inv.data = new
    inv.title = derive_title(new)
    inv.status = "draft"
    db.commit()


@router.post("")
def create(db: Session = Depends(get_db)):
    inv = Investigation(data=InvestigationData().model_dump())
    db.add(inv)
    db.commit()
    return serialize(inv, db)


@router.get("")
def list_all(db: Session = Depends(get_db)):
    rows = db.scalars(select(Investigation).order_by(Investigation.updated_at.desc())).all()
    return [{"id": r.id, "title": r.title, "status": r.status, "version": r.version,
             "updated_at": r.updated_at.isoformat()} for r in rows]


@router.get("/{inv_id}")
def get_one(inv_id: int, db: Session = Depends(get_db)):
    return serialize(get_inv(db, inv_id), db)


@router.post("/{inv_id}/upload")
async def upload(inv_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Step 1 of document intake: file -> plain text. The text is then sent to /chat as document_text."""
    get_inv(db, inv_id)
    content = await file.read()
    try:
        text, meta = extract_text(file.filename or "upload", content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"name": file.filename, "text": text, "chars": len(text), **meta}


@router.patch("/{inv_id}/fields")
def edit_field(inv_id: int, body: ManualFieldEdit, db: Session = Depends(get_db)):
    """Reviewer override of a single scalar field (review step, not the primary workflow)."""
    inv = get_inv(db, inv_id)
    if not valid_path(body.path):
        raise HTTPException(400, "Unknown field")
    d = InvestigationData.model_validate(inv.data)
    set_field(d, body.path, body.value, source="user", accepted=True, force=True)
    commit_change(db, inv, d, source="user", actor="user", label=f"edit {body.path}")
    return serialize(inv, db)


@router.post("/{inv_id}/accept")
def accept(inv_id: int, body: dict[str, Any], db: Session = Depends(get_db)):
    """Reviewer accepts an AI-suggested value (field path, or hypotheses.H1 / capa.C1 / gaps.G1)."""
    inv = get_inv(db, inv_id)
    paths = body.get("paths") or [body.get("path", "")]
    d = InvestigationData.model_validate(inv.data)
    for path in paths:
        prov = d.provenance.get(path) or Provenance(source="ai_inference")
        prov.accepted = True
        d.provenance[path] = prov
        if path.startswith("capa."):
            for c in d.capa:
                if c.id == path.split(".", 1)[1]:
                    c.accepted = True
    commit_change(db, inv, d, source="user", actor="user", label=f"accept {len(paths)} item(s)")
    return serialize(inv, db)


@router.patch("/{inv_id}/items/{section}/{item_id}")
def edit_item(inv_id: int, section: str, item_id: str, body: dict[str, Any], db: Session = Depends(get_db)):
    """Edit a hypothesis / CAPA / gap / evidence item (e.g. owner, due date, wording, resolved)."""
    if section not in ("hypotheses", "capa", "gaps", "evidence"):
        raise HTTPException(400, "Unknown section")
    inv = get_inv(db, inv_id)
    d = InvestigationData.model_validate(inv.data)
    items = getattr(d, section)
    target = next((i for i in items if i.id == item_id), None)
    if not target:
        raise HTTPException(404, "Item not found")
    protected = {"id", "status", "confirmed_by"}
    for k, v in body.items():
        if k in protected or k not in type(target).model_fields:
            continue
        setattr(target, k, v)
    d.provenance[f"{section}.{item_id}"] = Provenance(source="user", accepted=True)
    if section == "capa":
        target.accepted = True  # a reviewer who edits a CAPA owns it; AI re-analysis must not overwrite it
    commit_change(db, inv, d, source="user", actor="user", label=f"edit {section}.{item_id}")
    return serialize(inv, db)


@router.post("/{inv_id}/hypotheses/{hid}/confirm")
def confirm(inv_id: int, hid: str, body: ConfirmRequest, db: Session = Depends(get_db)):
    """Only a person can confirm a root cause. The AI cannot reach this status."""
    inv = get_inv(db, inv_id)
    d = InvestigationData.model_validate(inv.data)
    h = next((h for h in d.hypotheses if h.id == hid), None)
    if not h:
        raise HTTPException(404, "Hypothesis not found")
    if not body.confirmed_by.strip():
        raise HTTPException(400, "confirmed_by is required")
    h.status, h.confirmed_by = "confirmed", body.confirmed_by.strip()
    d.provenance[f"hypotheses.{hid}"] = Provenance(source="user", accepted=True)
    commit_change(db, inv, d, source="user", actor="user", label=f"confirm {hid}")
    return serialize(inv, db)


@router.post("/{inv_id}/hypotheses/{hid}/reject")
def reject(inv_id: int, hid: str, db: Session = Depends(get_db)):
    inv = get_inv(db, inv_id)
    d = InvestigationData.model_validate(inv.data)
    h = next((h for h in d.hypotheses if h.id == hid), None)
    if not h:
        raise HTTPException(404, "Hypothesis not found")
    h.status, h.confirmed_by = "rejected", None
    commit_change(db, inv, d, source="user", actor="user", label=f"reject {hid}")
    return serialize(inv, db)


@router.post("/{inv_id}/save")
def save(inv_id: int, db: Session = Depends(get_db)):
    inv = get_inv(db, inv_id)
    d = InvestigationData.model_validate(inv.data)
    if not d.deviation.description:
        raise HTTPException(400, "Nothing to save yet")
    if not any(h.status == "confirmed" for h in d.hypotheses):
        raise HTTPException(400, "Confirm at least one root cause (a person must sign off) before saving.")
    inv.status = "saved"
    db.commit()
    return serialize(inv, db)


@router.post("/{inv_id}/undo")
def undo(inv_id: int, db: Session = Depends(get_db)):
    inv = get_inv(db, inv_id)
    snap = db.scalars(select(Snapshot).where(Snapshot.investigation_id == inv_id).order_by(Snapshot.id.desc())).first()
    if not snap:
        raise HTTPException(400, "Nothing to undo")
    old = inv.data
    inv.version += 1
    write_audit(db, inv, old, snap.data, source="user", actor="user", tool=None)
    inv.data = snap.data
    inv.title = derive_title(snap.data)
    inv.status = "draft"
    db.delete(snap)
    db.commit()
    return serialize(inv, db)


@router.get("/{inv_id}/audit")
def audit(inv_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditEntry).where(AuditEntry.investigation_id == inv_id).order_by(AuditEntry.id.desc()).limit(200)).all()
    return [{"version": r.version, "path": r.path, "old": (r.old_value or {}).get("v"), "new": (r.new_value or {}).get("v"),
             "source": r.source, "actor": r.actor, "tool": r.tool, "at": r.created_at.isoformat()} for r in rows]
