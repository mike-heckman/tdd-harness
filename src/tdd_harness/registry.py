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
        detailed_description: str = "",
        syntax_examples: object = None,
    ):  # Reason: JSON schema
        """
        Initialize a ToolEntry.
        """
        self.name = name
        self.type = tool_type
        self.description = description
        self.input_schema = input_schema
        self.func = func
        self.detailed_description = detailed_description
        self.syntax_examples = syntax_examples


class ToolRegistry:
    """
    Central registry for managing and dispatching tools.
    """

    def __init__(
        self,
        mcp_client: MCPClientProtocol | None = None,
        tracker: object | None = None,
        tool_configs: dict[str, Any] | None = None,
    ):
        """
        Initialize the ToolRegistry.
        """
        self.mcp_client = mcp_client
        self.tracker = tracker
        self.tool_configs = tool_configs or {}
        self.tools: dict[str, ToolEntry] = {}

        self.register_python_tool(
            self.get_tool_help, name="get_tool_help", description="Get detailed help and schema for a tool"
        )

    def _get_tool_metadata(self, tool_name: str) -> dict:
        if isinstance(self.tool_configs, dict):
            for file_cfg in self.tool_configs.values():
                if isinstance(file_cfg, dict):
                    tools_block = file_cfg.get("tools", {})
                    if isinstance(tools_block, dict) and tool_name in tools_block:
                        val = tools_block[tool_name]
                        if isinstance(val, dict):
                            return val
                        elif isinstance(val, list):
                            return {"errors": val}
        return {}

    def _get_tool_config_block(self, tool_name: str) -> dict:
        if isinstance(self.tool_configs, dict):
            for file_cfg in self.tool_configs.values():
                if isinstance(file_cfg, dict):
                    tools_block = file_cfg.get("tools", {})
                    if isinstance(tools_block, dict) and tool_name in tools_block:
                        val = tools_block[tool_name]
                        if isinstance(val, dict):
                            return val
                        elif isinstance(val, list):
                            return {"errors": val}
        return {}

    def get_tool_help(self, tool_name: str) -> dict[str, Any]:
        """
        Get detailed help and schema for a specific tool.
        """
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        tool = self.tools[tool_name]
        return {
            "name": tool.name,
            "description": tool.description,
            "detailed_description": tool.detailed_description,
            "syntax_examples": tool.syntax_examples,
            "schema": tool.input_schema,
        }

    async def initialize(self) -> None:
        """
        Initialize the registry by loading tools from the MCP client.
        """
        if self.mcp_client:
            mcp_tools = await self.mcp_client.get_tools()
            for t in mcp_tools:
                tool_name = str(t["name"])
                meta = self._get_tool_metadata(tool_name)

                self.tools[tool_name] = ToolEntry(
                    name=tool_name,
                    tool_type=ToolType.MCP,
                    description=str(t.get("description", "")),
                    input_schema=t.get("input_schema", {}),  # type: ignore
                    detailed_description=meta.get("detailed_description", ""),
                    syntax_examples=meta.get("syntax_examples"),
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
            if param_name in ("self", "previous_failures", "config"):
                continue
            properties[param_name] = {"type": "string"}  # Defaulting to string for test simplicity
            required.append(param_name)

        schema = {"type": "object", "properties": properties, "required": required}

        meta = self._get_tool_metadata(tool_name)

        self.tools[tool_name] = ToolEntry(
            name=tool_name,
            tool_type=ToolType.PYTHON,
            description=tool_desc,
            input_schema=schema,
            func=func,
            detailed_description=meta.get("detailed_description", ""),
            syntax_examples=meta.get("syntax_examples"),
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

        previous_failures = 0
        if self.tracker and hasattr(self.tracker, "get_previous_failures"):
            previous_failures = self.tracker.get_previous_failures(name)  # type: ignore

        try:
            if tool.type == ToolType.MCP and self.mcp_client:
                resp = await self.mcp_client.call_tool(name, arguments)

                is_error = False
                error_msg = ""
                content = None

                if isinstance(resp, dict):
                    if resp.get("isError"):
                        is_error = True
                        error_msg = str(resp.get("content", resp))
                    else:
                        content = resp["content"][0]["text"] if "content" in resp else resp
                else:
                    content = resp

                if is_error:
                    raise RuntimeError(error_msg)

                return ToolCallResult(content=content)
            else:
                if tool.func:
                    sig = inspect.signature(tool.func)
                    if "previous_failures" in sig.parameters:
                        arguments["previous_failures"] = previous_failures
                    if "config" in sig.parameters:
                        arguments["config"] = self._get_tool_config_block(name)

                    result = tool.func(**arguments)
                    if inspect.iscoroutine(result):
                        result = await result
                    return ToolCallResult(content=result)
                return ToolCallResult(content=None, success=False, error="No function defined for tool")
        except Exception as e:
            error_msg = str(e)
            meta = self._get_tool_metadata(name)
            errors_config = meta.get("errors", [])

            hint = ""
            for err_cfg in errors_config:
                if isinstance(err_cfg, dict):
                    match_str = err_cfg.get("match", "")
                    if match_str and match_str in error_msg:
                        hints = err_cfg.get("hints", [])
                        if hints:
                            hint_idx = min(previous_failures, len(hints) - 1)
                            hint = hints[hint_idx]
                            break

            if hint:
                error_msg = f"{error_msg}\nHint: {hint}"

            return ToolCallResult(content=None, success=False, error=error_msg)

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
