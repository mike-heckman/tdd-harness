---
id: "0024"
title: "Refine LLMClient: Replace Placeholder Heuristics with ContextBuilder Integration"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/llm.py"
success_criteria:
  - "Remove all placeholder comments (e.g. 'for the sake of passing the tests', 'for this placeholder', 'for this simple implementation') and replace with production logic."
  - "The `chat()` method must accept OpenAI-compatible tool schemas and handle tool-call responses in a loop (matching the pattern used in `controller.py`'s sub-agents)."
  - "The `chat()` method must use the `Prompt` class (from task 0022) to load the system message and manage token caching, instead of relying on an opaque mock object."
  - "Compression must use the `compression_prompt.yaml` template loaded via `load_prompt_config` rather than a hardcoded string."
  - "The `LLMClient` must track conversation history (`self.history`) and prune it based on `keep_turns` from config, appending only the most recent N assistant/user turn pairs."
  - "Add or update unit tests in `tests/test_llm.py` to cover tool-call handling, history pruning by `keep_turns`, and compression using the real prompt template."
---
# Unit of Work: Refine LLMClient: Replace Placeholder Heuristics with ContextBuilder Integration

## Context
The `LLMClient.chat()` method currently contains placeholder heuristics ("1 char = 1 token") and hardcoded compression strings. It also does not support tool calls, meaning the controller bypasses `LLMClient` entirely and creates raw `AsyncOpenAI` clients for every sub-agent invocation. This task replaces all placeholder logic with production-grade implementations that integrate with the `Prompt` class and `ContextBuilder`.
