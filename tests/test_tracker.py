"""Tests for the tracker module."""

from src.tdd_harness.models.tool import ToolCall, ToolCallResponse
from src.tdd_harness.tracker import AntiThrashingTracker


def test_tracker_initialization():
    """Test tracker initialization."""
    tracker = AntiThrashingTracker(max_duplicate_failures=3, max_window_failures=2, window_size=5)

    assert tracker.max_duplicate_failures == 3
    assert tracker.max_window_failures == 2
    assert tracker.window_size == 5
    assert len(tracker.tool_call_hashes) == 0
    assert len(tracker.failure_window) == 0


def test_record_tool_call():
    """Test recording tool calls."""
    tracker = AntiThrashingTracker()

    # Record a successful call
    tracker.record_tool_call(
        ToolCall(tool_name="test_tool", arguments={"arg1": "value1"}), ToolCallResponse(success=True)
    )

    assert len(tracker.tool_call_hashes) == 1
    assert tracker.tool_call_hashes[0][1] is True

    # Record a failed call
    tracker.record_tool_call(
        ToolCall(tool_name="test_tool", arguments={"arg1": "value2"}), ToolCallResponse(success=False)
    )

    assert len(tracker.tool_call_hashes) == 2
    assert tracker.tool_call_hashes[1][1] is False


def test_duplicate_failures():
    """Test duplicate failure detection."""
    tracker = AntiThrashingTracker(max_duplicate_failures=3)

    # Record 2 duplicate failures (same hash)
    tracker.record_tool_call(
        ToolCall(tool_name="test_tool", arguments={"arg1": "value1"}), ToolCallResponse(success=False)
    )
    tracker.record_tool_call(
        ToolCall(tool_name="test_tool", arguments={"arg1": "value1"}), ToolCallResponse(success=False)
    )

    assert tracker.duplicate_failures == 1

    # Record a third duplicate failure - should trigger abort
    tracker.record_tool_call(
        ToolCall(tool_name="test_tool", arguments={"arg1": "value1"}), ToolCallResponse(success=False)
    )

    assert tracker.duplicate_failures == 2
    assert tracker.should_abort() is True


def test_window_failures():
    """Test window-based failure detection."""
    tracker = AntiThrashingTracker(max_window_failures=3, window_size=5)

    # Record 2 failures in a window of size 5
    for i in range(2):
        tracker.record_tool_call(ToolCall(tool_name=f"tool_{i}", arguments={"arg": i}), ToolCallResponse(success=False))

    # Should not abort yet (only 2 failures but max_window_failures is 3)
    assert tracker.should_abort() is False

    # Record a 3rd failure to exceed the window limit
    tracker.record_tool_call(ToolCall(tool_name="tool_2", arguments={"arg": 2}), ToolCallResponse(success=False))

    # Should abort now
    assert tracker.should_abort() is True


def test_reset():
    """Test resetting the tracker."""
    tracker = AntiThrashingTracker()

    # Add some data
    tracker.record_tool_call(
        ToolCall(tool_name="test_tool", arguments={"arg1": "value1"}), ToolCallResponse(success=False)
    )
    tracker.record_tool_call(
        ToolCall(tool_name="test_tool", arguments={"arg1": "value2"}), ToolCallResponse(success=True)
    )

    assert len(tracker.tool_call_hashes) == 2

    # Reset the tracker
    tracker.reset()

    assert len(tracker.tool_call_hashes) == 0
    assert len(tracker.failure_window) == 0
    assert tracker.duplicate_failures == 0
