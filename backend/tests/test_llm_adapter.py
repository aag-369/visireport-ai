import pytest

from app.cognitive.llm_client import LLMAdapterError, check_llm_health, generate_narrative


@pytest.mark.asyncio
async def test_generate_narrative_raises_when_no_key_configured():
    # ANTHROPIC_API_KEY / OPENAI_API_KEY are unset in the test environment -
    # this must raise a clear error, never fabricate narrative text.
    with pytest.raises(LLMAdapterError):
        await generate_narrative({"report_id": "VR-TEST", "defects": []})


@pytest.mark.asyncio
async def test_llm_health_reports_unconfigured():
    health = await check_llm_health()
    assert health["healthy"] is False
