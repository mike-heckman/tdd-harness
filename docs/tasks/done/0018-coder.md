---
id: "0018"
title: "Fix LLMClient configuration lookup"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/llm.py"
success_criteria:
  - "Refactor LLMClient's constructor and chat methods to retrieve API configuration settings from the nested config.llm dictionary rather than direct attributes."
  - "Support api_key, base_url, model, context_size, minimum_available_context, and keep_turns from config.llm."
  - "Ensure that all unit tests in tests/test_llm.py pass successfully."
---
# Unit of Work: Fix LLMClient configuration lookup

## Context
In `src/tdd_harness/llm.py`, `LLMClient` currently attempts to access configuration parameters using direct attributes on the config object (e.g. `self.config.api_key`, `self.config.base_url`). However, `TddHarnessConfig` holds configuration dictionaries on the `llm` key (e.g. `self.config.llm["api_key"]`). This causes an `AttributeError` when using a real `TddHarnessConfig`.
