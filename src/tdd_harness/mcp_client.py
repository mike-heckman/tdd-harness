"""
Client for interacting with Model Context Protocol servers.
"""

import asyncio
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class MCPClient:
    """
    Client for interacting with Model Context Protocol servers.
    """

    def __init__(self, server_config: dict[str, Any]):
        """
        Initialize the MCP client.

        Args:
            server_config: Configuration dictionary for the MCP server.
        """
        self.server_config = server_config
        self.session: ClientSession | None = None
        self.restart_policy = server_config.get("restart_policy", "exit")
        self.exit_stack = AsyncExitStack()
        self._retry_count = 0

    async def close(self) -> None:
        """
        Close the connection and cleanup resources.
        """
        await self.exit_stack.aclose()
        self.session = None

    async def handle_failure(self, error: Exception) -> None:
        """
        Handle MCP server failure according to restart policy.
        """
        if self.restart_policy == "exit":
            print(f"MCP server failure (policy='exit'): {error}", file=sys.stderr)
            sys.exit(1)
        elif self.restart_policy == "on-failure":
            if self._retry_count < 1:
                self._retry_count += 1
                await self.close()
                await self.connect()
            else:
                print(f"MCP server failure (policy='on-failure'): retries exhausted. {error}", file=sys.stderr)
        elif self.restart_policy == "always":
            await asyncio.sleep(1)
            await self.close()
            await self.connect()

    async def connect(self):
        """
        Connect to the MCP server.
        """
        if not self.server_config:
            return

        command = self.server_config.get("command")
        if not command:
            return

        args = self.server_config.get("args", [])
        env = self.server_config.get("env", None)

        server_parameters = StdioServerParameters(command=command, args=args, env=env)

        try:
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_parameters))
            self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
            self._retry_count = 0  # Reset retry count on successful connection
        except Exception as e:
            await self.handle_failure(e)

    async def get_tools(self) -> list[dict[str, Any]]:
        """
        Retrieve available tools from the MCP server.

        Returns:
            A list of tool definitions.
        """
        if not self.server_config or not self.session:
            return []

        try:
            result = await self.session.list_tools()
            return [tool.model_dump() for tool in result.tools]
        except Exception as e:
            await self.handle_failure(e)
            return []

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:  # Reason: Can return any object
        """
        Call a specific tool on the MCP server.

        Args:
            name: The name of the tool to call.
            arguments: The arguments to pass to the tool.

        Returns:
            The result of the tool call.
        """
        if not self.server_config or not self.session:
            return {}

        try:
            result = await self.session.call_tool(name, arguments=arguments)
            return result
        except Exception as e:
            await self.handle_failure(e)
            raise
