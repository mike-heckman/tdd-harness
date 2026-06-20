from unittest.mock import AsyncMock, MagicMock

import pytest

from src.tdd_harness.mcp_client import MCPClient
from src.tdd_harness.registry import ToolRegistry, ToolType


@pytest.fixture
def mock_mcp_client():
    client = MagicMock(spec=MCPClient)
    client.get_tools = AsyncMock(
        return_value=[
            {
                "name": "mcp_tool",
                "description": "A tool from MCP",
                "input_schema": {"type": "object", "properties": {"arg1": {"type": "string"}}, "required": ["arg1"]},
            }
        ]
    )
    client.call_tool = AsyncMock(return_value={"content": [{"type": "text", "text": "mcp response"}]})
    return client


@pytest.fixture
def registry(mock_mcp_client):
    return ToolRegistry(mcp_client=mock_mcp_client)


@pytest.mark.asyncio
async def test_registry_initialization(registry, mock_mcp_client):
    await registry.initialize()
    assert "mcp_tool" in registry.tools
    assert registry.tools["mcp_tool"].type == ToolType.MCP


@pytest.mark.asyncio
async def test_register_python_tool(registry):
    def my_tool(x: int) -> str:
        return f"hello {x}"

    registry.register_python_tool(my_tool, name="py_tool", description="a py tool")
    assert "py_tool" in registry.tools
    assert registry.tools["py_tool"].type == ToolType.PYTHON


@pytest.mark.asyncio
async def test_dispatch_mcp_tool(registry, mock_mcp_client):
    await registry.initialize()
    result = await registry.dispatch("mcp_tool", {"arg1": "val"})
    assert result.content == "mcp response"
    mock_mcp_client.call_tool.assert_called_once_with("mcp_tool", {"arg1": "val"})


@pytest.mark.asyncio
async def test_dispatch_python_tool(registry):
    def my_tool(x: int) -> str:
        return f"hello {x}"

    registry.register_python_tool(my_tool, name="py_tool")
    result = await registry.dispatch("py_tool", {"x": 10})
    assert result.content == "hello 10"


@pytest.mark.asyncio
async def test_get_openai_schemas(registry, mock_mcp_client):
    await registry.initialize()
    registry.register_python_tool(lambda x: x, name="py_tool", description="desc")

    schemas = registry.get_openai_schemas()
    assert len(schemas) == 2

    mcp_schema = next(s for s in schemas if s["function"]["name"] == "mcp_tool")
    assert mcp_schema["type"] == "function"
    assert mcp_schema["function"]["name"] == "mcp_tool"

    py_schema = next(s for s in schemas if s["function"]["name"] == "py_tool")
    assert py_schema["function"]["name"] == "py_tool"
    assert py_schema["function"]["description"] == "desc"


@pytest.mark.asyncio
async def test_dispatch_unknown_tool(registry):
    with pytest.raises(ValueError, match="Unknown tool"):
        await registry.dispatch("unknown", {})
