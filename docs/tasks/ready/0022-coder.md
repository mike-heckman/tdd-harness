---
id: "0022"
title: "Implement Prompt Class with Token Cache & Hash Invalidation"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/prompt.py"
success_criteria:
  - "Create a `Prompt` class in `src/tdd_harness/prompt.py` that loads a prompt YAML file from `.tdd-harness/prompts/<name>.yaml` using `load_prompt_config`."
  - "The class must compute the SHA256 hash of the loaded prompt text on initialization."
  - "The class must read `.prompt-cache.yaml` from the project root (mutable state file) and look up the stored `prompt_hash` for its prompt name."
  - "If the computed hash does not match the stored `prompt_hash`, the `token_counts` dictionary for that prompt must be cleared and the new hash written to `.prompt-cache.yaml`."
  - "Implement `token_size(model: str) -> int | None` which returns the cached token count for the given model, or `None` if not cached."
  - "Implement `update_token_size(model: str, count: int)` which writes the token count for the given model to the `.prompt-cache.yaml` state file."
  - "Implement `get_system_message() -> Context` which returns a `Context` object of type `ContextType.SYSTEM` containing the prompt text."
  - "Add unit tests in `tests/test_prompt.py` covering hash computation, cache hit, cache invalidation on prompt change, and token size read/write."
---
# Unit of Work: Implement Prompt Class with Token Cache & Hash Invalidation

## Context
The SDD specifies a dedicated `Prompt` class that manages prompt loading, SHA256 hash-based cache invalidation, and per-model token counting. The `LLMClient` already expects a `prompt` object with `token_size()` and `update_token_size()` methods, but this object is currently mocked in tests and does not exist in the source. The `.prompt-cache.yaml` file must be mutable (project root) while `.tdd-harness/prompts/*.yaml` remains read-only.
