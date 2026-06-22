# Performance Audit Report: LLM Call Efficiency & Adapter Orchestration

**Date:** 2026-06-22
**Ticket:** 0033-performance.md
**Auditor:** Coder Agent

## 1. LLM API Calls & Redundancy
- **Observation**: During the Blue and Green phases, if an implementation fails, the `_generate_post_mortem` method makes an expensive secondary LLM call to summarize the failure. Redundant LLM calls were being triggered when identical test failure outputs occurred consecutively. 
- **Resolution**: Implemented a caching layer (`_post_mortem_cache`) in `TDDLoopController` using `hashlib.sha256` on the `(filepath, raw_error)` tuple. This caches post-mortem summaries, preventing duplicate LLM calls for identical error states.

## 2. Unnecessary Subprocess Spawning in Orchestration
- **Observation**: The `pre_flight_validation` in `controller.py` invoked both `run_test` and `run_coverage` sequentially. Since both methods default to `orchestrate_global` when no file is specified, the entire test suite and coverage generation were running twice, heavily impacting performance.
- **Resolution**: Refactored `pre_flight_validation` to call `run_test_and_coverage` once. Since the `orchestrate_global` method inherently generates both testing and coverage outputs in a single execution pass natively, this eliminated the redundant subprocess spawning.

## 3. ContextBuilder Token Deadlock Prevention
- **Observation**: The token checking logic in `LLMClient` attempted history compression whenever available tokens dropped below the minimum. However, if the statically sized incoming tokens (`system_message` + `task_context`) themselves consumed the entire context window, compression was triggered indefinitely, leading to a Context Deadlock.
- **Resolution**: Added a strict static context check in `LLMClient.chat()`. If `self._context_size - (system_tokens + incoming_tokens) < self._minimum_available_context`, it immediately aborts with a `RuntimeError("Context Exhausted")` per SDD §5, bypassing infinite loops.

## 4. AntiThrashingTracker Overhead
- **Observation**: The `AntiThrashingTracker` hashed tool arguments using `hash(tuple(sorted(tool_call.arguments.items())))`. This caused severe overhead and `TypeError: unhashable type` errors when tool arguments contained nested dictionaries or lists, requiring Python to attempt deep-hashing.
- **Resolution**: Replaced the native `tuple` hash with a deterministic string serialization (`json.dumps(..., sort_keys=True)`) passed through `hashlib.sha256`. This stabilizes hash computation time to O(N) relative to the serialized size and eliminates unhashable type exceptions.

## Additional Unit Tests
The following unit tests were introduced to verify and guarantee the performance fixes:

- `test_generate_post_mortem` in `tests/test_controller.py`: Verifies the `_post_mortem_cache` effectively blocks duplicate LLM calls.
- `test_llm_client_context_exhausted` in `tests/test_llm.py`: Asserts that `RuntimeError` is raised properly if incoming static tokens exceed the context constraints without incorrectly looping into compression.
- `test_pre_flight_validation` in `tests/test_controller.py`: Updated mock to assert `run_test_and_coverage` executes only a single pass.
