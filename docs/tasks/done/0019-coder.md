---
id: "0019"
title: "Fix AntiThrashingTracker sliding window tracking"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/tracker.py"
success_criteria:
  - "Update AntiThrashingTracker.record_tool_call() to correctly represent the rolling window history of tool executions."
  - "Ensure successful tool calls are recorded in the failure_window (or that success pushes out older failures) so that failures do not persist indefinitely and trigger false positive aborts."
  - "Write unit tests to verify that a successful tool call prevents subsequent unrelated failures from prematurely triggering an abort."
  - "All unit tests in tests/test_tracker.py must pass successfully."
---
# Unit of Work: Fix AntiThrashingTracker sliding window tracking

## Context
The `AntiThrashingTracker` maintains a sliding window of failures using `self.failure_window = deque(maxlen=window_size)`. However, only failed tool calls are appended to it. Because successful tool calls do not affect `failure_window`, the length of the window eventually reaches the threshold of failures and causes a permanent abort, even when there are thousands of successful calls in between.
