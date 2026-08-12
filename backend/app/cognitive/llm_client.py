"""Provider-agnostic LLM adapter for NCR narrative + root-cause + CAPA
synthesis. Real Anthropic/OpenAI SDK calls, selected via LLM_PROVIDER.

This module never fabricates narrative text. If no API key is configured,
or the provider call fails, `LLMAdapterError` is raised and the caller
(the consumer worker) records a FAILED status - the frontend must show
that failure, not templated placeholder copy.
"""
import json
import logging

from app.config import get_settings

logger = logging.getLogger("visireport.cognitive")

SYSTEM_PROMPT = """You are a quality engineering assistant generating an ISO 13485:2016 \
Non-Conformance Report (NCR) narrative for a medical-device PCB assembly (PCBA) automated \
optical inspection (AOI) result. Given a structured JSON defect payload, produce:

1. A narrative_text: a concise, professional NCR narrative describing what was found \
(reference ISO 13485 Clause 8.3 - Control of Nonconforming Product).
2. A root_cause_text: a plausible root-cause hypothesis grounded in the specific defect \
classes and counts present (reference Clause 8.5.2 - Corrective Action).
3. A capa object with three string fields: immediate_containment, root_cause_elimination, \
and preventive_measure - concrete CAPA actions specific to the defects found.

Respond with ONLY a JSON object with keys: narrative_text, root_cause_text, capa \
(capa having keys immediate_containment, root_cause_elimination, preventive_measure). \
No markdown fencing, no commentary outside the JSON."""


class LLMAdapterError(RuntimeError):
    pass


def _build_user_prompt(payload: dict) -> str:
    return (
        "Structured AOI inspection payload (VISIREPORT_SCHEMA):\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Generate the NCR narrative, root cause hypothesis, and CAPA JSON now."
    )


def _parse_llm_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMAdapterError(f"LLM response was not valid JSON: {exc}") from exc

    required = {"narrative_text", "root_cause_text", "capa"}
    if not required.issubset(data.keys()):
        raise LLMAdapterError(f"LLM response missing required keys: {required - data.keys()}")
    capa_required = {"immediate_containment", "root_cause_elimination", "preventive_measure"}
    if not capa_required.issubset(data["capa"].keys()):
        raise LLMAdapterError(f"LLM CAPA response missing keys: {capa_required - data['capa'].keys()}")
    return data


async def _call_anthropic(settings, payload: dict) -> dict:
    if not settings.anthropic_api_key:
        raise LLMAdapterError(
            "ANTHROPIC_API_KEY is not configured. Set it in .env to enable narrative generation."
        )
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:  # pragma: no cover
        raise LLMAdapterError(f"anthropic SDK not installed: {exc}") from exc

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(payload)}],
        )
    except Exception as exc:
        raise LLMAdapterError(f"Anthropic API call failed: {exc}") from exc

    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    parsed = _parse_llm_json(text)
    parsed["model_used"] = settings.anthropic_model
    return parsed


async def _call_openai(settings, payload: dict) -> dict:
    if not settings.openai_api_key:
        raise LLMAdapterError(
            "OPENAI_API_KEY is not configured. Set it in .env to enable narrative generation."
        )
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover
        raise LLMAdapterError(f"openai SDK not installed: {exc}") from exc

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(payload)},
            ],
        )
    except Exception as exc:
        raise LLMAdapterError(f"OpenAI API call failed: {exc}") from exc

    text = response.choices[0].message.content
    parsed = _parse_llm_json(text)
    parsed["model_used"] = settings.openai_model
    return parsed


async def generate_narrative(payload: dict) -> dict:
    """Dispatch to the configured LLM provider. Returns dict with keys
    narrative_text, root_cause_text, capa, model_used."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    logger.info("Generating narrative via provider=%s for report_id=%s", provider, payload.get("report_id"))

    if provider == "anthropic":
        return await _call_anthropic(settings, payload)
    elif provider == "openai":
        return await _call_openai(settings, payload)
    else:
        raise LLMAdapterError(f"Unknown LLM_PROVIDER '{settings.llm_provider}' (expected anthropic|openai)")


async def check_llm_health() -> dict:
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        configured = bool(settings.anthropic_api_key)
    elif provider == "openai":
        configured = bool(settings.openai_api_key)
    else:
        return {"healthy": False, "detail": f"Unknown provider '{settings.llm_provider}'"}
    return {
        "healthy": configured,
        "provider": provider,
        "detail": "API key configured" if configured else "API key missing - set it in .env",
    }
