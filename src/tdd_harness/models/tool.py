"""
Tool models for defining harness operations.
"""

from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """
    Represents a request to execute a specific tool.
    """

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    """
    Represents the result of executing a tool.
    """

    success: bool
    output: str | None = None
    errors: list[str] | None = None
    data: dict[str, Any] | None = None
