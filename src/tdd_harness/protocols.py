"""
Protocol definitions for tdd-harness to ensure strict type checking without circular imports.
"""

from typing import Protocol

from .config import TddHarnessConfig
from .models.tool import ToolCall, ToolCallResponse


class ConfigLoaderProtocol(Protocol):
    """
    Protocol for loading the harness configuration.
    """

    def get_config(self) -> TddHarnessConfig:
        """
        Get the tdd-harness configuration.

        Returns:
            The loaded TddHarnessConfig object.
        """
        ...


class TrackerProtocol(Protocol):
    """
    Protocol for tracking tool call execution and failures.
    """

    def record_tool_call(self, tool_call: ToolCall, response: ToolCallResponse) -> None:
        """
        Record a tool call and its result.

        Args:
            tool_call: The requested tool call.
            response: The result of the tool call.
        """
        ...

    def should_abort(self) -> bool:
        """
        Determine if the harness should abort due to thrashing.

        Returns:
            True if the harness should abort, False otherwise.
        """
        ...

    def get_previous_failures(self, tool_name: str) -> int:
        """
        Get the number of consecutive failures for a specific tool.

        Args:
            tool_name: The name of the tool.

        Returns:
            The number of consecutive failures.
        """
        ...

    def reset(self) -> None:
        """
        Reset all tracking state.
        """
        ...
