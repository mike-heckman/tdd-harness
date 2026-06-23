"""
Custom exceptions for the TDD Harness.
"""


class HarnessAbort(Exception):
    """
    Exception raised to abort the harness run.
    """

    pass


class MCPFatalError(Exception):
    """
    Exception raised when an MCP server encounters a fatal error.
    """

    pass
