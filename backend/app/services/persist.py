"""Persistence helpers: field-level audit diff + snapshots for undo."""
from sqlalchemy.orm import Session

from ..models import AuditEntry, Investigation, Snapshot
from ..schemas import InvestigationData

LIST_SECTIONS = ("hypotheses", "evidence", "gaps", "capa")


def _flatten(data: dict) -> dict:
    flat = {}
    for scope in ("deviation", "batch"):
        for k, v in data.get(scope, {}).items():
            flat[f"{scope}.{k}"] = v
    for section in LIST_SECTIONS:
        for item in data.get(section, []):
            flat[f"{section}.{item['id']}"] = item
    flat["why_chain"] = data.get("why_chain", [])
    flat["health"] = data.get("health", {})
    return flat


def write_audit(db: Session, inv: Investigation, old: dict, new: dict, *, source: str, actor: str, tool: str | None) -> list[str]:
    a, b = _flatten(old), _flatten(new)
    changed = []
    for path in sorted(set(a) | set(b)):
        if a.get(path) != b.get(path):
            changed.append(path)
            db.add(AuditEntry(
                investigation_id=inv.id, version=inv.version, path=path,
                old_value={"v": a.get(path)}, new_value={"v": b.get(path)},
                source=source, actor=actor, tool=tool,
            ))
    return changed


def snapshot(db: Session, inv: Investigation, label: str) -> None:
    db.add(Snapshot(investigation_id=inv.id, version=inv.version, data=inv.data, label=label))


def derive_title(data: dict) -> str:
    b, dv = data.get("batch", {}), data.get("deviation", {})
    parts = [dv.get("title") or "", b.get("product_name") or "", b.get("batch_number") or ""]
    title = " – ".join(p for p in parts if p)
    return title[:300] or "Untitled investigation"


def validated(data: dict) -> dict:
    return InvestigationData.model_validate(data).model_dump()
