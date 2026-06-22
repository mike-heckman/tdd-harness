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
    assert len(schemas) == 3

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


def test_schema_generation_types(registry):
    def my_tool(s: str, i: int, f: float, b: bool, lst: list, untyped) -> str:
        return "hi"

    registry.register_python_tool(my_tool, name="type_tool")
    schema = registry.tools["type_tool"].input_schema
    assert schema["properties"]["s"]["type"] == "string"
    assert schema["properties"]["i"]["type"] == "integer"
    assert schema["properties"]["f"]["type"] == "number"
    assert schema["properties"]["b"]["type"] == "boolean"
    assert schema["properties"]["lst"]["type"] == "array"
    assert schema["properties"]["untyped"]["type"] == "string"  # Default
    assert set(schema["required"]) == {"s", "i", "f", "b", "lst", "untyped"}


@pytest.mark.asyncio
async def test_registry_with_tracker_and_config():
    tracker = MagicMock()
    tracker.get_previous_failures.return_value = 1

    tool_configs = {
        "file1": {
            "tools": {
                "py_tool": {
                    "detailed_description": "det_desc",
                    "syntax_examples": ["ex1"],
                    "errors": [{"match": "Oops", "hints": ["Hint 0", "Hint 1", "Hint 2"]}],
                },
                "list_tool": ["error1", "error2"],
            }
        }
    }

    registry = ToolRegistry(tracker=tracker, tool_configs=tool_configs)

    def py_tool(x: int, previous_failures: int, config: dict) -> str:
        if x == 0:
            raise ValueError("Oops something went wrong")
        return f"{previous_failures}-{config.get('detailed_description')}"

    registry.register_python_tool(py_tool)
    assert registry.tools["py_tool"].detailed_description == "det_desc"

    res = await registry.dispatch("py_tool", {"x": 1})
    assert res.content == "1-det_desc"
    assert res.success is True

    res = await registry.dispatch("py_tool", {"x": 0})
    assert res.success is False
    assert "Oops something went wrong" in res.error
    assert "Hint: Hint 1" in res.error


@pytest.mark.asyncio
async def test_dispatch_mcp_tool_error(registry, mock_mcp_client):
    await registry.initialize()
    mock_mcp_client.call_tool.return_value = {"isError": True, "content": "MCP failed"}
    res = await registry.dispatch("mcp_tool", {"arg1": "val"})
    assert res.success is False
    assert "MCP failed" in res.error


@pytest.mark.asyncio
async def test_dispatch_mcp_tool_string_response(registry, mock_mcp_client):
    await registry.initialize()
    mock_mcp_client.call_tool.return_value = "raw string response"
    res = await registry.dispatch("mcp_tool", {"arg1": "val"})
    assert res.content == "raw string response"


@pytest.mark.asyncio
async def test_dispatch_async_python_tool(registry):
    async def async_tool():
        return "async success"

    registry.register_python_tool(async_tool)
    res = await registry.dispatch("async_tool", {})
    assert res.content == "async success"


def test_get_tool_help(registry):
    registry.register_python_tool(lambda x: x, name="t1", description="desc")
    help_data = registry.get_tool_help("t1")
    assert help_data["description"] == "desc"

    err_data = registry.get_tool_help("unknown")
    assert "error" in err_data


def test_get_tool_config_block_list_errors():
    tool_configs = {"f": {"tools": {"t": ["e1", "e2"]}}}
    from src.tdd_harness.registry import ToolRegistry

    registry = ToolRegistry(tool_configs=tool_configs)
    meta = registry._get_tool_metadata("t")
    assert meta == {"errors": ["e1", "e2"]}

    cfg = registry._get_tool_config_block("t")
    assert cfg == {"errors": ["e1", "e2"]}


@pytest.mark.asyncio
async def test_dispatch_no_func():
    from src.tdd_harness.registry import ToolEntry, ToolRegistry, ToolType

    registry = ToolRegistry()
    registry.tools["nofunc"] = ToolEntry(name="nofunc", tool_type=ToolType.PYTHON, description="", input_schema={})
    res = await registry.dispatch("nofunc", {})
    assert res.success is False
    assert "No function defined" in res.error
