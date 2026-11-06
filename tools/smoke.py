"""End-to-end smoke test against a running backend (mock or real LLM).

    backend\\.venv\\Scripts\\python.exe tools\\smoke.py
"""
import json
import sys
from pathlib import Path

import httpx

BASE = "http://localhost:8000/api/investigations"
PDF = Path(__file__).resolve().parent.parent / "samples" / "DEV-2026-0412_residual_solvent.pdf"
c = httpx.Client(timeout=120)


def chat(inv_id: int, **body) -> dict:
    nodes, last_state, msg = [], None, None
    with c.stream("POST", f"{BASE}/{inv_id}/chat", json=body) as r:
        r.raise_for_status()
        event = None
        for line in r.iter_lines():
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                payload = json.loads(line[6:])
                if event == "node":
                    nodes.append(payload["node"])
                elif event == "state":
                    last_state = payload["data"]
                elif event == "message":
                    msg = payload
                elif event == "error":
                    sys.exit(f"STREAM ERROR: {payload}")
    return {"nodes": nodes, "state": last_state, "msg": msg}


def show(title: str, res: dict) -> None:
    d = res["state"]
    print(f"\n=== {title}\nnodes: {' > '.join(res['nodes'])}\nreply: {res['msg']['content']}")
    print("changed:", res["msg"]["changed"][:12])
    print("health:", d["health"]["evidence_sufficiency"], d["health"]["readiness"])
    print("hypotheses:", [(h["id"], h["status"], len(h["evidence_for"])) for h in d["hypotheses"]])
    print("gaps open:", [g["id"] for g in d["gaps"] if not g["resolved"]])


inv = c.post(BASE).json()
iid = inv["id"]

up = c.post(f"{BASE}/{iid}/upload", files={"file": (PDF.name, PDF.read_bytes(), "application/pdf")}).json()
print("uploaded:", up["name"], up["chars"], "chars,", up["pages"], "page(s)")
r1 = chat(iid, message="", document_text=up["text"], document_name=up["name"])
show("1. INGEST (PDF)", r1)
d = r1["state"]
print("batch:", d["batch"]["product_name"], "|", d["batch"]["batch_number"], "|", d["batch"]["affected_quantity"])
print("why_chain last:", d["why_chain"][-1]["answer"][:90], "| steps:", len(d["why_chain"]))
print("warnings:", d["health"]["warnings"])

r2 = chat(iid, message="Sorry, the batch number is CHG260712A and affected quantity is 50 kg (2 HDPE drums)")
show("2. EDIT", r2)
d = r2["state"]
assert d["batch"]["batch_number"] == "CHG260712A", d["batch"]
assert d["batch"]["product_name"] == "Atorvastatin Calcium API", "edit lost other fields!"
assert len(d["evidence"]) >= 5, "evidence lost"

r3 = chat(iid, message="The dryer log shows vacuum rose to 300 mbar after 3 hours.")
show("3. EDIT (new evidence)", r3)

r4 = chat(iid, message="", action="challenge")
show("4. CHALLENGE", r4)

# human review: confirm H1, accept a CAPA, save
conf = c.post(f"{BASE}/{iid}/hypotheses/H1/confirm", json={"confirmed_by": "A. Rao (QA)"}).json()
print("\nH1 status after human confirm:", [h["status"] for h in conf["data"]["hypotheses"] if h["id"] == "H1"])
c.post(f"{BASE}/{iid}/accept", json={"path": "capa.C2"})
saved = c.post(f"{BASE}/{iid}/save").json()
print("saved status:", saved["status"], "| version", saved["version"], "| messages", len(saved["messages"]))
und = c.post(f"{BASE}/{iid}/undo").json()
print("undo ->", [h["status"] for h in und["data"]["hypotheses"] if h["id"] == "H1"], "status", und["status"])
print("audit rows:", len(c.get(f"{BASE}/{iid}/audit").json()))
print("\nSMOKE OK")
