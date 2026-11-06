"""Print Groq rate-limit headers per model for the configured key (never prints the key)."""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.config import settings  # noqa: E402

MODELS = sys.argv[1:] or ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
for m in MODELS:
    body = {"model": m, "messages": [{"role": "user", "content": "Say ok"}], "max_tokens": 5}
    if m.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"
    r = httpx.post("https://api.groq.com/openai/v1/chat/completions", json=body, timeout=60,
                   headers={"Authorization": f"Bearer {settings.groq_api_key}"})
    h = r.headers
    print(m, r.status_code,
          "| req/day:", h.get("x-ratelimit-limit-requests"), "left", h.get("x-ratelimit-remaining-requests"),
          "| tokens/min:", h.get("x-ratelimit-limit-tokens"), "left", h.get("x-ratelimit-remaining-tokens"),
          "| reset tok:", h.get("x-ratelimit-reset-tokens"))
