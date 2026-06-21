from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tdd_harness.context import Context, ContextType
from src.tdd_harness.llm import LLMClient


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.llm = {
        "api_key": "test-key",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4",
        "context_size": 8000,
        "minimum_available_context": 1000,
        "keep_turns": 1,
    }
    return config


@pytest.fixture
def mock_prompt():
    prompt = MagicMock()
    # Initially no cached size
    prompt.token_size.return_value = None
    prompt.update_token_size = MagicMock()
    # Return a mock system message object
    mock_sys_msg = MagicMock()
    mock_sys_msg.content = "You are a helpful assistant."
    prompt.get_system_message.return_value = mock_sys_msg
    return prompt


@pytest.fixture
def mock_config_loader(mock_config, mock_prompt):
    loader = MagicMock()
    loader.get_config.return_value = mock_config
    loader.get_prompt.return_value = mock_prompt
    return loader


@pytest.mark.asyncio
async def test_llm_client_baseline_extraction(mock_config, mock_prompt, mock_config_loader):
    """Tests that the system message token size is extracted from API response if not cached."""

    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 150  # This should include system message
    mock_response.choices[0].message.content = "hello"

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_completions = MagicMock()
        mock_client.chat.completions = mock_completions
        mock_completions.create = AsyncMock(return_value=mock_response)

        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        await client.chat([Context(text="hello", context_type=ContextType.TASK_CONTEXT, token_count=5)])

        # Verify baseline extraction logic
        # If system message was 150 and user msg was small, prompt.update_token_size should be called
        mock_prompt.update_token_size.assert_called()


@pytest.mark.asyncio
async def test_llm_client_context_compression_trigger(mock_config, mock_prompt, mock_config_loader):
    """Tests that compression is triggered when remaining context falls below threshold."""

    mock_prompt.token_size.return_value = 500
    messages = [Context(text="a" * 7000, context_type=ContextType.TASK_CONTEXT, token_count=7000)]

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_completions = MagicMock()
        mock_client.chat.completions = mock_completions

        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        # Mock compression response
        comp_response = MagicMock()
        comp_response.choices[0].message.content = "Summary of history"
        comp_response.usage.prompt_tokens = 100

        # Mock actual chat response
        chat_response = MagicMock()
        chat_response.choices[0].message.content = "Final answer"
        chat_response.usage.prompt_tokens = 100

        mock_completions.create = AsyncMock()
        mock_completions.create.side_effect = [comp_response, chat_response]

        await client.chat(messages)

        # Should have called create at least twice: once for compression, once for the actual chat
        assert mock_completions.create.call_count >= 2


@pytest.mark.asyncio
async def test_llm_client_compression_rebuilds_history(mock_config, mock_prompt, mock_config_loader):
    """Tests that history is correctly rebuilt after compression."""
    mock_prompt.token_size.return_value = 500

    # Large message to trigger compression
    messages = [Context(text="a" * 7000, context_type=ContextType.TASK_CONTEXT, token_count=7000)]

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_completions = MagicMock()
        mock_client.chat.completions = mock_completions

        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        # 1. Compression call
        comp_response = MagicMock()
        comp_response.choices[0].message.content = "Summarized content"
        comp_response.usage.prompt_tokens = 50

        # 2. Final call
        chat_response = MagicMock()
        chat_response.choices[0].message.content = "Final response"
        chat_response.usage.prompt_tokens = 50

        mock_completions.create = AsyncMock()
        mock_completions.create.side_effect = [comp_response, chat_response]

        await client.chat(messages)

        # Verify the messages sent in the second call include the summary
        # Call 0: compression prompt (the messages being compressed)
        # Call 1: the new messages (system + summary + remaining)
        args, kwargs = mock_completions.create.call_args_list[1]
        sent_messages = kwargs["messages"]

        # Should contain system message and the summary
        assert any("Summarized content" in m.get("content", "") for m in sent_messages)


@pytest.mark.parametrize(
    "missing_key, error_msg",
    [
        ("model", "Model not specified in LLM configuration"),
        ("context_size", "Context size not specified in LLM configuration"),
        ("minimum_available_context", "Minimum available context not specified in LLM configuration"),
        ("keep_turns", "Keep turns not specified in LLM configuration"),
    ],
)
def test_llm_client_missing_config(mock_config, mock_prompt, missing_key, error_msg):
    """Tests that ValueError is raised if required configuration is missing."""
    mock_config.llm.pop(missing_key)
    loader = MagicMock()
    loader.get_config.return_value = mock_config
    loader.get_prompt.return_value = mock_prompt

    with pytest.raises(ValueError, match=error_msg):
        LLMClient(loader, mock_prompt)


def test_llm_client_missing_multiple_configs(mock_config, mock_prompt):
    """Tests that ValueError is raised with multiple accumulated errors."""
    mock_config.llm.pop("model")
    mock_config.llm.pop("context_size")

    loader = MagicMock()
    loader.get_config.return_value = mock_config
    loader.get_prompt.return_value = mock_prompt

    with pytest.raises(ValueError) as excinfo:
        LLMClient(loader, mock_prompt)

    error_msg = str(excinfo.value)
    assert "Model not specified in LLM configuration" in error_msg
    assert "Context size not specified in LLM configuration" in error_msg
