"""Compare latency / token use / JSON validity of Groq models on the hypothesize prompt.

    set PYTHONIOENCODING=utf-8 && backend\\.venv\\Scripts\\python.exe -I tools\\model_bench.py [model[:effort] ...]
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from langchain_groq import ChatGroq  # noqa: E402

from app.ai import prompts  # noqa: E402
from app.config import settings  # noqa: E402
from app.schemas import HypothesizeOut  # noqa: E402

INV = {
    "batch": {"product_name": "Atorvastatin Calcium API", "batch_number": "ATC260915A", "test_result": "IPA 5800 ppm vs NMT 5000"},
    "evidence": [
        {"id": "E1", "description": "Operator ended cycle at 9 h of 12 h after LOD 0.4%"},
        {"id": "E2", "description": "Bed depth about 4 cm; validated range not stated"},
        {"id": "E3", "description": "Only start-of-cycle gauge reading recorded"},
    ],
    "hypotheses": [], "why_chain": [],
}


async def bench(spec: str):
    model, _, effort = spec.partition(":")
    kw = {"reasoning_effort": effort} if effort else {}
    client = ChatGroq(model=model, api_key=settings.groq_api_key, temperature=0.1, max_retries=0, timeout=90, **kw)
    client = client.bind(response_format={"type": "json_object"})
    msgs = [
        ("system", prompts.HYPOTHESIZE + "\nReturn ONE JSON object matching: " + json.dumps(HypothesizeOut.model_json_schema())),
        ("human", "INVESTIGATION:\n" + json.dumps(INV)),
    ]
    t = time.time()
    try:
        r = await client.ainvoke(msgs)
    except Exception as e:  # noqa: BLE001
        print(f"{spec}: FAILED {time.time() - t:.1f}s {type(e).__name__}: {str(e)[:200]}")
        return
    u = r.response_metadata.get("token_usage", {})
    try:
        out = HypothesizeOut.model_validate_json(r.content)
        valid = f"valid ({len(out.hypotheses)} hyps, {len(out.why_chain)} whys)"
    except Exception as e:  # noqa: BLE001
        valid = f"INVALID: {str(e)[:120]}"
    print(f"{spec}: {time.time() - t:.1f}s | prompt={u.get('prompt_tokens')} completion={u.get('completion_tokens')} "
          f"queue={u.get('queue_time')} api_total={u.get('total_time')} | {valid}")


async def main():
    specs = sys.argv[1:] or ["openai/gpt-oss-120b:low", "openai/gpt-oss-20b:low", "qwen/qwen3.8-27b"]
    for s in specs:
        await bench(s)


asyncio.run(main())
