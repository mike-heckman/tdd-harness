"""
Module for the unified tool registry system.
"""

import inspect
from collections.abc import Callable
from enum import Enum
from typing import Any, Protocol


class ToolType(Enum):
    """
    Types of tools supported by the registry.
    """

    MCP = "mcp"
    PYTHON = "python"


class ToolCallResult:
    """
    Result of a tool execution.
    """

    def __init__(
        self, content: object, success: bool = True, error: str | None = None
    ):  # Reason: Can be any response object
        """
        Initialize a ToolCallResult.
        """
        self.content = content
        self.success = success
        self.error = error


class MCPClientProtocol(Protocol):
    """
    Protocol defining the expected interface for an MCP client.
    """

    async def get_tools(self) -> list[dict[str, object]]:
        """
        Get tools.
        """
        ...  # Reason: JSON schema objects

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        """
        Call a tool.
        """
        ...  # Reason: Dynamic RPC payloads


class ToolEntry:
    """
    An entry in the tool registry.
    """

    def __init__(
        self,
        name: str,
        tool_type: ToolType,
        description: str,
        input_schema: dict[str, object],
        func: Callable | None = None,
    ):  # Reason: JSON schema
        """
        Initialize a ToolEntry.
        """
        self.name = name
        self.type = tool_type
        self.description = description
        self.input_schema = input_schema
        self.func = func


class ToolRegistry:
    """
    Central registry for managing and dispatching tools.
    """

    def __init__(self, mcp_client: MCPClientProtocol | None = None):
        """
        Initialize the ToolRegistry.
        """
        self.mcp_client = mcp_client
        self.tools: dict[str, ToolEntry] = {}

    async def initialize(self) -> None:
        """
        Initialize the registry by loading tools from the MCP client.
        """
        if self.mcp_client:
            mcp_tools = await self.mcp_client.get_tools()
            for t in mcp_tools:
                tool_name = str(t["name"])
                self.tools[tool_name] = ToolEntry(
                    name=tool_name,
                    tool_type=ToolType.MCP,
                    description=str(t.get("description", "")),
                    input_schema=t.get("input_schema", {}),  # type: ignore
                )

    def register_python_tool(self, func: Callable, name: str | None = None, description: str | None = None) -> None:
        """
        Register a local Python function as a tool.
        """
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or ""

        # Very basic schema generation for testing
        sig = inspect.signature(func)
        properties = {}
        required = []
        for param_name, _param in sig.parameters.items():
            if param_name == "self":
                continue
            properties[param_name] = {"type": "string"}  # Defaulting to string for test simplicity
            required.append(param_name)

        schema = {"type": "object", "properties": properties, "required": required}

        self.tools[tool_name] = ToolEntry(
            name=tool_name, tool_type=ToolType.PYTHON, description=tool_desc, input_schema=schema, func=func
        )

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        """
        Execute a tool by its name.

        Args:
            name: The name of the tool to execute.
            arguments: A dictionary of arguments for the tool.

        Returns:
            A ToolCallResult object.
        """
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        tool = self.tools[name]
        try:
            if tool.type == ToolType.MCP and self.mcp_client:
                resp = await self.mcp_client.call_tool(name, arguments)
                # Handle standard MCP response format
                content = resp["content"][0]["text"] if isinstance(resp, dict) and "content" in resp else resp
                return ToolCallResult(content=content)
            else:
                if tool.func:
                    result = tool.func(**arguments)
                    return ToolCallResult(content=result)
                return ToolCallResult(content=None, success=False, error="No function defined for tool")
        except Exception as e:
            return ToolCallResult(content=None, success=False, error=str(e))

    def get_openai_schemas(self) -> list[dict[str, Any]]:
        """
        Generate OpenAI-compatible tool schemas.

        Returns:
            A list of tool schemas.
        """
        schemas = []
        for tool in self.tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema},
                }
            )
        return schemas
