"""
Base adapter module.
"""

from abc import ABC, abstractmethod

from src.tdd_harness.models.tool import ToolCall, ToolCallResponse


class Adapter(ABC):
    """
    Base class for all toolchain adapters.
    """

    supported_extensions: list[str] = []
    language: str = ""

    @abstractmethod
    def run(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Run the adapter.
        """
        pass


class TestAdapter(Adapter):
    """
    Base interface for test execution adapters.
    """

    @abstractmethod
    def run(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Execute tests based on the provided tool call.

        Args:
            tool_call: The request detailing what to test.

        Returns:
            The test execution result.
        """
        pass


class LintAdapter(Adapter):
    """
    Base interface for linting adapters.
    """

    @abstractmethod
    def run(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Execute linting based on the provided tool call.

        Args:
            tool_call: The request detailing what to lint.

        Returns:
            The linting result.
        """
        pass


class CoverageAdapter(Adapter):
    """
    Base interface for coverage adapters.
    """

    @abstractmethod
    def run(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Execute coverage based on the provided tool call.

        Args:
            tool_call: The request detailing what to cover.

        Returns:
            The coverage result.
        """
        pass

    @abstractmethod
    def parse(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Parse coverage data based on the provided tool call.

        Args:
            tool_call: The request detailing what coverage to parse.

        Returns:
            The coverage parsing result.
        """
        pass
