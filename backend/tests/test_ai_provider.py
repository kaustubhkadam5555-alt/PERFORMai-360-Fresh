import pytest
from fastapi import HTTPException

from app.ai.provider import (
    AnthropicLLMProvider,
    DisabledLLMProvider,
    MockLLMProvider,
    OllamaLLMProvider,
    OpenAILLMProvider,
    get_llm_provider,
)


@pytest.mark.asyncio
async def test_mock_provider_generation_empty():
    provider = MockLLMProvider(context=None)
    assert provider.name == "mock"
    assert provider.model_name == "mock-eval-engine-v1"
    assert provider.is_available is True

    result = await provider.generate_analysis(prompt="Analyze work", system_instruction="System rule")
    assert "strengths" in result
    assert "improvement_opportunities" in result
    assert "suggested_discussion_questions" in result
    assert len(result["suggested_discussion_questions"]) > 0
    assert len(result["overall_limitations"]) > 0


@pytest.mark.asyncio
async def test_disabled_provider_behavior():
    provider = DisabledLLMProvider()
    assert provider.name == "none"
    assert provider.is_available is False

    with pytest.raises(HTTPException) as exc_info:
        await provider.generate_analysis(prompt="Prompt", system_instruction="Sys")
    assert exc_info.value.status_code == 503
    assert "disabled or unconfigured" in exc_info.value.detail


def test_provider_factory():
    mock_p = get_llm_provider(provider_override="mock")
    assert isinstance(mock_p, MockLLMProvider)

    disabled_p = get_llm_provider(provider_override="none")
    assert isinstance(disabled_p, DisabledLLMProvider)

    disabled_p2 = get_llm_provider(provider_override="disabled")
    assert isinstance(disabled_p2, DisabledLLMProvider)

    openai_p = get_llm_provider(provider_override="openai")
    assert isinstance(openai_p, OpenAILLMProvider)

    anthropic_p = get_llm_provider(provider_override="anthropic")
    assert isinstance(anthropic_p, AnthropicLLMProvider)

    ollama_p = get_llm_provider(provider_override="ollama")
    assert isinstance(ollama_p, OllamaLLMProvider)


def test_provider_no_credentials_exposure():
    openai_p = OpenAILLMProvider()
    anthropic_p = AnthropicLLMProvider()

    # Representation or error logging should never expose plaintext secrets
    assert "sk-" not in str(openai_p)
    assert "sk-ant" not in str(anthropic_p)
