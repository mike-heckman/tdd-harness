"""
Context and payload assembly classes.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ContextType(Enum):
    """
    Enum mapping conceptual context to its API role.
    """

    SYSTEM = "system"
    TASK_CONTEXT = "user"
    TASK_CRITERIA = "user"
    FILE_SOURCE = "user"
    TEST_CONCEPTS = "user"
    TRACEBACK = "user"
    COVERAGE_REPORT = "user"
    DRAFT_CODE = "user"
    POST_MORTEM_SUMMARY = "user"
    TOOL_RESULT = "tool"
    CHAT_HISTORY = "assistant"


@dataclass
class Context:
    """
    A discrete block of memory for context payloads.
    """

    text: str
    context_type: ContextType
    token_count: int | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    creation_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = field(default_factory=dict)
    is_count_estimated: bool = True
    is_compressible: bool = True

    def __post_init__(self):
        """
        Initialize instance-level flags based on context type.
        """
        if self.token_count is None:
            self.token_count = len(self.text) // 4
            self.is_count_estimated = True

        if self.context_type == ContextType.COVERAGE_REPORT:
            self.is_compressible = False
        elif self.context_type == ContextType.POST_MORTEM_SUMMARY:
            self.is_compressible = True


class ContextBuilder:
    """
    A stateful stack manager for context payloads (Singleton).
    """

    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "ContextBuilder":
        """
        Create or return the singleton instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._stack = []
        return cls._instance

    def __init__(self):
        """
        Initialize the context stack.
        """
        pass

    def clear(self) -> None:
        """
        Clear the context stack.
        """
        self._stack.clear()

    def add_context(self, new: Context) -> None:
        """
        Push a new context object to the stack.
        """
        self._stack.append(new)

    def remove_context(self, context_id: str) -> None:
        """
        Remove a context by ID.
        """
        self._stack = [c for c in self._stack if c.id != context_id]

    def replace_with_summary(self, context_ids: list[str], summary_text: str) -> None:
        """
        Remove specified contexts and inject a new summary context.
        """
        insert_index = len(self._stack)
        for i, c in enumerate(self._stack):
            if c.id in context_ids:
                insert_index = i
                break

        self._stack = [c for c in self._stack if c.id not in context_ids]
        token_count = len(summary_text) // 4
        new_summary = Context(text=summary_text, context_type=ContextType.POST_MORTEM_SUMMARY, token_count=token_count)
        self._stack.insert(insert_index, new_summary)

    def get_list_tokens(self, context_types: list[ContextType]) -> int:
        """
        Return an instant O(1) sum of cached token_counts for matching contexts.
        """
        return sum((c.token_count or 0) for c in self._stack if c.context_type in context_types)

    def get_context(
        self, context_types: list[ContextType] | None = None, metadata_filters: dict[str, str] | None = None
    ) -> list[Context]:
        """
        Return raw Context objects, optionally filtering by type or metadata.
        """
        result = self._stack
        if context_types is not None:
            result = [c for c in result if c.context_type in context_types]
        if metadata_filters is not None:
            for key, value in metadata_filters.items():
                result = [c for c in result if c.metadata.get(key) == value]
        return result
