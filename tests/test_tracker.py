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

    # Record 2 failures for the same tool in a window of size 5
    for i in range(2):
        tracker.record_tool_call(ToolCall(tool_name="test_tool", arguments={"arg": i}), ToolCallResponse(success=False))

    # Should not abort yet (only 2 failures but max_window_failures is 3)
    assert tracker.should_abort() is False

    # Record a 3rd failure for the same tool to exceed the window limit
    tracker.record_tool_call(ToolCall(tool_name="test_tool", arguments={"arg": 2}), ToolCallResponse(success=False))

    # Should abort now
    assert tracker.should_abort() is True


def test_interleaved_tool_calls_in_window():
    """Test that interleaved successful calls of different tools don't prevent abort if one tool fails repeatedly."""
    tracker = AntiThrashingTracker(max_window_failures=3, window_size=10)

    # Edit fails
    tracker.record_tool_call(ToolCall(tool_name="edit", arguments={"a": 1}), ToolCallResponse(success=False))
    # Read succeeds
    tracker.record_tool_call(ToolCall(tool_name="read", arguments={"b": 1}), ToolCallResponse(success=True))
    # Edit fails
    tracker.record_tool_call(ToolCall(tool_name="edit", arguments={"a": 2}), ToolCallResponse(success=False))
    # Read succeeds
    tracker.record_tool_call(ToolCall(tool_name="read", arguments={"b": 2}), ToolCallResponse(success=True))

    # We have 2 edit failures in the window, but we need 3 to abort
    assert tracker.should_abort() is False

    # Edit fails again
    tracker.record_tool_call(ToolCall(tool_name="edit", arguments={"a": 3}), ToolCallResponse(success=False))

    # Now we have 3 edit failures in the window, so it should abort
    assert tracker.should_abort() is True


def test_successful_call_prevents_abort():
    """Test that successful calls push out old failures from the window."""
    tracker = AntiThrashingTracker(max_window_failures=3, window_size=5)

    # Record 2 failures
    tracker.record_tool_call(ToolCall(tool_name="fail1", arguments={"a": 1}), ToolCallResponse(success=False))
    tracker.record_tool_call(ToolCall(tool_name="fail2", arguments={"a": 2}), ToolCallResponse(success=False))

    # Record 4 successes
    for i in range(4):
        tracker.record_tool_call(ToolCall(tool_name=f"success{i}", arguments={}), ToolCallResponse(success=True))

    # The first 2 failures should be pushed out of the window of size 5
    # Record another failure
    tracker.record_tool_call(ToolCall(tool_name="fail3", arguments={"a": 3}), ToolCallResponse(success=False))

    # Should not abort because there is only 1 failure in the current window
    assert tracker.should_abort() is False


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
