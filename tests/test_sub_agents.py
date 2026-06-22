from unittest.mock import AsyncMock, MagicMock

import pytest

from src.tdd_harness.context import ContextType
from src.tdd_harness.sub_agents import PostMortemSubAgent, ResearchSubAgent, ReviewSubAgent


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client._model = "test-model"
    client.chat = AsyncMock(return_value="Mocked response")
    return client


@pytest.fixture
def mock_prompt():
    prompt = MagicMock()
    sys_msg = MagicMock()
    sys_msg.text = "Mock system message"
    prompt.get_system_message.return_value = sys_msg
    return prompt


@pytest.fixture
def mock_registry():
    registry = MagicMock()
    registry.get_openai_schemas.return_value = [
        {"function": {"name": "get_file_content"}},
        {"function": {"name": "search_web"}},
    ]
    # We also mock registry.tools lookup for the mcp check
    mock_tool = MagicMock()
    mock_tool.type.value = "mcp"
    registry.tools = {"get_file_content": mock_tool, "search_web": mock_tool}
    return registry


@pytest.mark.asyncio
async def test_review_sub_agent(mock_llm_client, mock_prompt, mock_registry):
    agent = ReviewSubAgent(mock_llm_client, mock_prompt)

    res = await agent.review("task", "file1.py", "diff", mock_registry)

    assert res == "Mocked response"
    mock_llm_client.chat.assert_called_once()

    # Verify contexts
    contexts = mock_llm_client.chat.call_args[0][0]
    assert len(contexts) == 2
    assert contexts[0].context_type == ContextType.SYSTEM
    assert contexts[1].context_type == ContextType.TASK_CONTEXT
    assert "task" in contexts[1].text

    # Verify tools filter
    tools = mock_llm_client.chat.call_args[1]["tools"]
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "get_file_content"


@pytest.mark.asyncio
async def test_post_mortem_sub_agent(mock_llm_client, mock_prompt):
    # Setup prompt that uses format()
    sys_msg = MagicMock()
    sys_msg.text = "File: {filepath}, Code: {code}, Error: {raw_error}"
    mock_prompt.get_system_message.return_value = sys_msg

    agent = PostMortemSubAgent(mock_llm_client, mock_prompt)

    res = await agent.generate("file1.py", "print(1)", "SyntaxError")

    assert res == "Mocked response"
    mock_llm_client.chat.assert_called_once()

    contexts = mock_llm_client.chat.call_args[0][0]
    assert len(contexts) == 1
    assert contexts[0].context_type == ContextType.TASK_CONTEXT
    assert "File: file1.py, Code: print(1), Error: SyntaxError" in contexts[0].text


@pytest.mark.asyncio
async def test_research_sub_agent(mock_llm_client, mock_prompt, mock_registry):
    agent = ResearchSubAgent(mock_llm_client, mock_prompt)

    res = await agent.ask("query text", mock_registry)

    assert res == "Mocked response"
    mock_llm_client.chat.assert_called_once()

    contexts = mock_llm_client.chat.call_args[0][0]
    assert len(contexts) == 2
    assert contexts[0].context_type == ContextType.SYSTEM
    assert contexts[1].context_type == ContextType.TASK_CONTEXT
    assert "query text" in contexts[1].text

    # Verify tools filter
    tools = mock_llm_client.chat.call_args[1]["tools"]
    assert len(tools) == 2
    names = [t["function"]["name"] for t in tools]
    assert "get_file_content" in names
    assert "search_web" in names
