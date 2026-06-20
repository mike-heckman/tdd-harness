"""
Anti-thrashing tracker for tdd-harness.
"""

import hashlib
from collections import deque

from src.tdd_harness.models.tool import ToolCall, ToolCallResponse


class AntiThrashingTracker:
    """
    Tracks tool call hashes and failure states to prevent infinite loops.
    """

    def __init__(self, max_duplicate_failures: int = 5, max_window_failures: int = 3, window_size: int = 10):
        """
        Initialize the tracker.

        Args:
            max_duplicate_failures: Maximum number of duplicate failed requests before aborting
            max_window_failures: Maximum number of failed requests in a window before aborting
            window_size: Size of the sliding window for tracking failures
        """
        self.max_duplicate_failures = max_duplicate_failures
        self.max_window_failures = max_window_failures
        self.window_size = window_size

        # Track tool call hashes and their success status
        self.tool_call_hashes: list[tuple[str, bool]] = []

        # Track the sliding window of failures
        self.failure_window: deque = deque(maxlen=window_size)

        # Track duplicate failures
        self.duplicate_failures = 0
        self.last_failure_hash = None

    def record_tool_call(self, tool_call: ToolCall, response: ToolCallResponse) -> None:
        """
        Record a tool call and its result.

        Args:
            tool_call: The requested tool call
            response: The result of the tool call
        """
        # Create a hash of the tool call for tracking
        # Convert dict to sorted tuple of items for hashing
        arg_tuple = tuple(sorted(tool_call.arguments.items()))
        call_hash = hashlib.sha256(f"{tool_call.tool_name}:{hash(arg_tuple)}".encode()).hexdigest()

        # Record the call
        self.tool_call_hashes.append((call_hash, response.success))

        # Update failure tracking
        if not response.success:
            self.failure_window.append(call_hash)

            # Check for duplicate failures
            if call_hash == self.last_failure_hash:
                self.duplicate_failures += 1
            else:
                self.duplicate_failures = 0
                self.last_failure_hash = call_hash
        else:
            # Reset duplicate failure counter on success
            self.duplicate_failures = 0

    def should_abort(self) -> bool:
        """
        Determine if the harness should abort due to thrashing.

        Returns:
            True if the harness should abort, False otherwise
        """
        # Check for too many duplicate failures
        if self.duplicate_failures >= self.max_duplicate_failures:
            return True

        # Check for too many failures in the window
        # We check if the number of failures in the window meets or exceeds max_window_failures
        if len(self.failure_window) >= self.max_window_failures:
            return True

        return False

    def reset(self) -> None:
        """
        Reset all tracking state.
        """
        self.tool_call_hashes.clear()
        self.failure_window.clear()
        self.duplicate_failures = 0
        self.last_failure_hash = None
