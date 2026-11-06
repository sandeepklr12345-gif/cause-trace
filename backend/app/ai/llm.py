"""Single entry point for every LLM call: structured JSON in, validated Pydantic object out.

Groq's free tier allows 8k tokens/min *per model*, so each call names a tier and the work is
spread across three models (see config.py). Prompts stay compact for the same reason.
"""
import asyncio
import json
import logging
import re
import time
from typing import Literal, Type, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import settings
from . import mock

log = logging.getLogger("causetrace.llm")
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[llm] %(message)s"))
    log.addHandler(_h)

_rl = logging.getLogger("groq._base_client")  # shows when Groq asks us to wait (rate limits)
_rl.setLevel(logging.INFO)
_rl.addHandler(_h)

T = TypeVar("T", bound=BaseModel)
Tier = Literal["heavy", "alt", "fast"]

_clients: dict[str, object] = {}


def model_for(tier: Tier) -> str:
    return {"heavy": settings.groq_model, "alt": settings.groq_model_alt, "fast": settings.groq_model_fast}[tier]


def _client_for(model: str):
    if model not in _clients:
        from langchain_groq import ChatGroq

        extra = {}
        if model.startswith("openai/gpt-oss"):
            # gpt-oss are reasoning models; "low" keeps each call to a few seconds
            extra["reasoning_effort"] = settings.groq_reasoning_effort
        _clients[model] = ChatGroq(
            model=model, api_key=settings.groq_api_key, temperature=0.1,
            max_retries=5, timeout=90, **extra,
        ).bind(response_format={"type": "json_object"})
    return _clients[model]


def _is_daily_limit(e: Exception) -> bool:
    return type(e).__name__ == "RateLimitError" and "per day" in str(e)


async def _invoke(tier: Tier, msgs):
    """Call the tier's model; if it has used up its daily token allowance, fall back to the other configured model."""
    primary = model_for(tier)
    order = [primary] + [m for m in dict.fromkeys((settings.groq_model, settings.groq_model_alt)) if m != primary]
    wait = ""
    for model in order:
        try:
            return await _client_for(model).ainvoke(msgs), model
        except Exception as e:  # noqa: BLE001
            if not _is_daily_limit(e):
                raise
            m = re.search(r"try again in ([0-9hms.]+)", str(e))
            wait = f" Try again in {m.group(1)}." if m else ""
            log.warning("%s hit its daily token limit; trying the next model", model)
    raise RuntimeError("Groq daily token limit reached on every configured model." + wait +
                       " Set MOCK_LLM=true to keep working with canned responses, or use another Groq key.")


def _strip(node):
    """Drop titles/defaults/descriptions from a JSON schema: the model only needs shapes and enums.
    Keys under `properties` are FIELD NAMES (e.g. a field called "title") and must be kept."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k in ("title", "default", "description"):
                continue
            out[k] = {name: _strip(spec) for name, spec in v.items()} if k == "properties" else _strip(v)
        return out
    if isinstance(node, list):
        return [_strip(v) for v in node]
    return node


def schema_hint(schema: Type[BaseModel]) -> str:
    return json.dumps(_strip(schema.model_json_schema()), separators=(",", ":"))


def _clean(node):
    """gpt-oss in JSON mode sometimes leaves stray '' or ',' items in arrays; drop them instead of burning a retry."""
    if isinstance(node, dict):
        return {k: _clean(v) for k, v in node.items()}
    if isinstance(node, list):
        items = [_clean(v) for v in node if not (isinstance(v, str) and not re.sub(r"[\s,;.]", "", v))]
        if any(isinstance(v, dict) for v in items):  # an array of objects never legitimately contains bare strings
            items = [v for v in items if isinstance(v, dict)]
        return items
    return node


def _extract_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    return _clean(json.loads(text))


async def structured_call(schema: Type[T], system: str, user: str, ctx: dict | None = None, tier: Tier = "heavy") -> T:
    """Call the model and return a validated `schema` instance.

    In mock mode, returns canned data derived from `ctx` (see mock.py).
    On invalid JSON / schema mismatch, retries once with the validation error fed back.
    """
    ctx = ctx or {}
    if settings.use_mock:
        await asyncio.sleep(0.5)  # make node progress visible in the UI
        return mock.respond(schema, {**ctx, "user": ctx.get("user", user)})

    messages = [
        ("system", f"{system}\n\nReturn ONE JSON object (no prose, no markdown) valid for this JSON Schema:\n{schema_hint(schema)}"),
        ("human", user),
    ]
    last_error = ""
    for _ in range(2):
        msgs = list(messages)
        if last_error:
            msgs.append(("human", f"Your previous answer was invalid: {last_error}\nReturn corrected JSON only."))
        t0 = time.time()
        resp, used_model = await _invoke(tier, msgs)
        usage = resp.response_metadata.get("token_usage", {})
        log.info("%s via %s: %.1fs, prompt=%s completion=%s", schema.__name__, used_model, time.time() - t0,
                 usage.get("prompt_tokens"), usage.get("completion_tokens"))
        try:
            return schema.model_validate(_extract_json(resp.content))
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            last_error = str(e)[:600]
            log.warning("%s invalid, retrying: %s", schema.__name__, last_error.replace("\n", " ")[:400])
    raise RuntimeError(f"Model returned invalid structured output for {schema.__name__}: {last_error}")
