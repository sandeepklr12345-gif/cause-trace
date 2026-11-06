# CauseTrace: AI-assisted Root Cause Analysis for API manufacturing

Split-screen app. The RCA form on the left is filled only by the AI copilot on the right (document, pasted text or chat).
Every AI value carries provenance, and only a person can confirm a root cause.

**Stack:** React + Redux Toolkit · FastAPI · LangGraph + Groq · PostgreSQL

> Keep this project, the sample documents and the demo videos private. The assignment forbids public repos.

## Run it

```bash
# 1. database (dev Postgres on port 5433)
docker compose up -d

# 2. backend
cd backend
python -m venv .venv && .venv\Scripts\pip install fastapi "uvicorn[standard]" "sqlalchemy>=2" "psycopg[binary]" pydantic-settings python-multipart pdfplumber langgraph langchain-groq httpx reportlab
copy .env.example .env      # then edit .env
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# 3. frontend
cd frontend && npm install && npm run dev      # http://localhost:5173
```

Real AI: in `backend/.env` set `GROQ_API_KEY=...` and `MOCK_LLM=false`.
With no key (or `MOCK_LLM=true`) the backend runs in **mock mode** (canned, deterministic responses) so the UI and flow can be tested.

### Groq models and limits (free tier, checked on this key)
`llama-3.3-70b-versatile` is no longer available, so the app uses `openai/gpt-oss-120b` (hypotheses, 5 Whys, gaps + CAPA)
and `openai/gpt-oss-20b` (extraction, edits, routing, critic). Limits seen: **8,000 tokens/min and 200,000 tokens/day per model**,
1,000 requests/day. `qwen/qwen3.8-27b` (1k output tokens/min) and `gpt-oss-safeguard-20b` (2k tokens/min) are too small.
- A full analysis turn costs roughly 5-7k tokens (about 35 turns/day on one model). Rehearse in mock mode, record with the real model.
- If one model hits its daily cap, calls fall back to the other automatically (`backend/app/ai/llm.py`).
- Back-to-back turns can wait ~10-30 s for the per-minute limit; pause 30 s between turns when recording.
- Tools: `tools/rate_limits.py`, `tools/model_bench.py`, `tools/graph_check.py` (per-node timing), `tools/debug_raw.py`.

Your own Postgres instead of Docker: set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/causetrace`.

Sample docs: `backend\.venv\Scripts\python tools\make_sample_docs.py` (writes to `samples/`).
Smoke test (backend running): `backend\.venv\Scripts\python tools\smoke.py`.

## How it works

```
route ─┬─ ingest ───┐
       ├─ edit ─────┼─▶ hypothesize ─▶ critic ─▶ gaps ─▶ capa ─▶ finalize
       ├─ analyze ──┘
       ├─ challenge ─▶ critic ─▶ finalize
       └─ question ──▶ answer ─▶ finalize
```

| Piece | File |
|---|---|
| LangGraph wiring | `backend/app/ai/graph.py` |
| Nodes (ingest, edit, hypothesize, critic, gaps, capa) | `backend/app/ai/nodes.py` |
| Prompts and guardrails | `backend/app/ai/prompts.py` |
| Groq call, JSON validation, retry | `backend/app/ai/llm.py` |
| Code-enforced safety rules + health score | `backend/app/ai/merge.py` |
| SSE chat endpoint | `backend/app/routers/chat.py` |
| Human review, confirm, save, undo | `backend/app/routers/investigations.py` |
| Redux store | `frontend/src/store/` |

**Design rules (enforced in code, not just in prompts)**
- The AI can only produce hypothesis status `suggested` or `supported` (supported needs linked evidence). `confirmed` requires a named person.
- "Operator error" chains are challenged by the critic node and pushed to system-level causes.
- Edits are patches: only the fields the user mentioned change. Every change is audited and can be undone.
- The evidence-sufficiency score is computed in code from evidence, hypothesis coverage and open high-priority gaps.
- Saving requires at least one human-confirmed root cause.
