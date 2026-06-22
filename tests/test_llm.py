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
        "keep_turns": 2,
    }
    return config


@pytest.fixture
def mock_prompt():
    prompt = MagicMock()
    prompt.token_size.return_value = None
    prompt.update_token_size = MagicMock()

    mock_sys_msg = MagicMock()
    mock_sys_msg.content = "You are a helpful assistant."
    mock_sys_msg.text = "You are a helpful assistant."
    mock_sys_msg.token_count = 10
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
    mock_prompt.get_system_message.return_value.token_count = 0

    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 150
    mock_response.choices[0].message.content = "hello"
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].message.model_dump.return_value = {"role": "assistant", "content": "hello"}

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_completions = MagicMock()
        mock_client.chat.completions = mock_completions
        mock_completions.create = AsyncMock(return_value=mock_response)

        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        await client.chat([Context(text="hello", context_type=ContextType.TASK_CONTEXT, token_count=5)])

        mock_prompt.update_token_size.assert_called_with("gpt-4", 150)


@pytest.mark.asyncio
async def test_llm_client_context_exhausted(mock_config, mock_prompt, mock_config_loader):
    """Tests that Context Exhausted RuntimeError is raised when system + incoming exceeds limits."""
    messages = [Context(text="huge", context_type=ContextType.TASK_CONTEXT, token_count=7500)]

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        with pytest.raises(RuntimeError, match="Context Exhausted"):
            await client.chat(messages)


@pytest.mark.asyncio
@patch("src.tdd_harness.llm.load_prompt_config")
async def test_llm_client_context_compression_trigger(
    mock_load_prompt_config, mock_config, mock_prompt, mock_config_loader
):
    """Tests that compression is triggered when remaining context falls below threshold."""
    mock_comp_config = MagicMock()
    mock_comp_config.prompt = "Compress this."
    mock_load_prompt_config.return_value = mock_comp_config

    from src.tdd_harness.context import ContextBuilder

    cb = ContextBuilder()
    cb.clear()
    cb.add_context(Context(text="a" * 30000, context_type=ContextType.CHAT_HISTORY, token_count=7000))
    messages = [Context(text="small", context_type=ContextType.TASK_CONTEXT, token_count=10)]

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_completions = MagicMock()
        mock_client.chat.completions = mock_completions

        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        comp_response = MagicMock()
        comp_response.choices[0].message.content = "Summary of history"
        comp_response.choices[0].message.tool_calls = None

        chat_response = MagicMock()
        chat_response.choices[0].message.content = "Final answer"
        chat_response.choices[0].message.tool_calls = None
        chat_response.choices[0].message.model_dump.return_value = {"role": "assistant", "content": "Final answer"}
        chat_response.usage.prompt_tokens = 100

        mock_completions.create = AsyncMock()
        mock_completions.create.side_effect = [comp_response, chat_response]

        await client.chat(messages)

        assert mock_completions.create.call_count >= 2
        mock_load_prompt_config.assert_called_with("compression_prompt")


@pytest.mark.asyncio
@patch("src.tdd_harness.llm.load_prompt_config")
async def test_llm_client_compression_rebuilds_history(
    mock_load_prompt_config, mock_config, mock_prompt, mock_config_loader
):
    """Tests that history is correctly rebuilt after compression."""
    mock_comp_config = MagicMock()
    mock_comp_config.prompt = "Compress this."
    mock_load_prompt_config.return_value = mock_comp_config

    messages = [Context(text="small task", context_type=ContextType.TASK_CONTEXT, token_count=10)]

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_completions = MagicMock()
        mock_client.chat.completions = mock_completions

        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        from src.tdd_harness.context import ContextBuilder

        cb = ContextBuilder()
        cb.clear()
        cb.add_context(
            Context(text="old history " + ("a" * 30000), context_type=ContextType.CHAT_HISTORY, token_count=7000)
        )

        comp_response = MagicMock()
        comp_response.choices[0].message.content = "Summarized content"
        comp_response.choices[0].message.tool_calls = None

        chat_response = MagicMock()
        chat_response.choices[0].message.content = "Final response"
        chat_response.choices[0].message.tool_calls = None
        chat_response.choices[0].message.model_dump.return_value = {"role": "assistant", "content": "Final response"}

        mock_completions.create = AsyncMock()
        mock_completions.create.side_effect = [comp_response, chat_response]

        await client.chat(messages)

        args, kwargs = mock_completions.create.call_args_list[1]
        sent_messages = kwargs["messages"]

        assert any("Summarized content" in m.get("content", "") for m in sent_messages)

        from src.tdd_harness.context import ContextBuilder

        cb = ContextBuilder()
        assert len(cb.get_context()) > 0
        cb.clear()


@pytest.mark.asyncio
async def test_llm_client_history_pruning(mock_config, mock_prompt, mock_config_loader):
    """Tests that history is pruned based on keep_turns."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "hello"
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].message.model_dump.return_value = {"role": "assistant", "content": "hello"}

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_completions = MagicMock()
        mock_client.chat.completions = mock_completions
        mock_completions.create = AsyncMock(return_value=mock_response)

        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        from src.tdd_harness.context import ContextBuilder

        cb = ContextBuilder()
        cb.clear()

        # config keeps 2 turns. Let's do 3 chats.
        await client.chat([Context(text="msg 1", context_type=ContextType.TASK_CONTEXT, token_count=5)])
        await client.chat([Context(text="msg 2", context_type=ContextType.TASK_CONTEXT, token_count=5)])
        await client.chat([Context(text="msg 3", context_type=ContextType.TASK_CONTEXT, token_count=5)])

        # Assert pruning (keep_turns=2, so we expect msg 2 and msg 3, plus their responses)
        chat_history = cb.get_context()
        assert any("msg 2" in m.text for m in chat_history)
        assert any("msg 3" in m.text for m in chat_history)

        # We expect the 'hello' responses from assistant turns 2 and 3 to be present.
        # But wait, pruning might have removed the first assistant response.
        # Just ensure msg 1 is fully gone.
        # Actually, "msg 1" was passed as TASK_CONTEXT. In the refactored code,
        # keep_turns only removes CHAT_HISTORY. The incoming TASK_CONTEXT might still be there.
        # Let's adjust to check just CHAT_HISTORY count.
        assistant_turns = cb.get_context([ContextType.CHAT_HISTORY])
        assert len(assistant_turns) == 2

        cb.clear()


@pytest.mark.asyncio
async def test_llm_client_tool_calls(mock_config, mock_prompt, mock_config_loader):
    """Tests that tool calls are handled and results are collected."""
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "my_tool"
    mock_tool_call.function.arguments = '{"arg": "val"}'
    mock_tool_call.model_dump.return_value = {
        "id": "call_123",
        "function": {"name": "my_tool", "arguments": '{"arg": "val"}'},
    }

    mock_tool_response = MagicMock()
    mock_tool_response.choices[0].message.content = None
    mock_tool_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_tool_response.choices[0].message.model_dump.return_value = {
        "role": "assistant",
        "tool_calls": [{"id": "call_123", "function": {"name": "my_tool", "arguments": '{"arg": "val"}'}}],
    }

    mock_final_response = MagicMock()
    mock_final_response.choices[0].message.content = "Done with tool"
    mock_final_response.choices[0].message.tool_calls = None
    mock_final_response.choices[0].message.model_dump.return_value = {"role": "assistant", "content": "Done with tool"}

    with patch("src.tdd_harness.llm.AsyncOpenAI", autospec=True) as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_completions = MagicMock()
        mock_client.chat.completions = mock_completions
        mock_completions.create = AsyncMock()
        mock_completions.create.side_effect = [mock_tool_response, mock_final_response]

        client = LLMClient(mock_config_loader, mock_prompt)
        client.client = mock_client

        from src.tdd_harness.context import ContextBuilder

        cb = ContextBuilder()
        cb.clear()

        mock_registry = MagicMock()
        mock_res = MagicMock()
        mock_res.success = True
        mock_res.content = "tool output"
        mock_registry.dispatch = AsyncMock(return_value=mock_res)

        final_msg = await client.chat(
            [Context(text="do tool", context_type=ContextType.TASK_CONTEXT, token_count=5)], registry=mock_registry
        )

        assert final_msg == "Done with tool"
        mock_registry.dispatch.assert_called_with("my_tool", {"arg": "val"})

        all_ctx = cb.get_context()
        assert any("do tool" in m.text for m in all_ctx)
        assert any(m.context_type == ContextType.TOOL_RESULT and "tool output" in m.text for m in all_ctx)
        assert any("Done with tool" in m.text for m in all_ctx)

        cb.clear()


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
