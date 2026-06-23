"""
Custom exceptions for the TDD Harness.
"""


class HarnessAbort(Exception):
    """
    Raised when the TDD loop should immediately halt due to anti-thrashing rules.
    """

    pass


class MCPFatalError(Exception):
    """
    Exception raised when an MCP server encounters a fatal error.
    """

    pass


class SecurityError(Exception):
    """
    Raised when an MCP tool attempts to access a file outside of the allowed workspace or phase boundaries.
    """

    pass


class PhaseValidationError(Exception):
    """
    Raised when phase exit validation fails.
    """

    pass
