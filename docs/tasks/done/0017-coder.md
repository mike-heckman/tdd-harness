---
id: '0017'
title: Context Builder & Phase Payload Assembly
success_criteria:
- Implement the `ContextType` Enum and `Context` dataclass (with auto-computed `token_count`).
- Implement the stateful `ContextBuilder` stack manager with `add_context`, `remove_context`, `replace_with_summary`, `get_list_tokens`, and `get_context`.
- Ensure `ContextBuilder` does NOT make any API calls or format OpenAI-specific JSON arrays.
- Refactor `LLMClient` to ingest `list[Context]` and handle the API-specific serialization (`role`, `content`) internally.
- Write unit tests ensuring `get_list_tokens` correctly sums values and `replace_with_summary` cleanly mutates the stack.
dependencies:
  prod: []
  dev: []
---
# Unit of Work: Context Builder & Phase Payload Assembly

## Context
Currently, context payloads are informally managed. To ensure robust token conservation and strict adherence to Phase guidelines, we need a formalized `ContextBuilder` that acts as a stateful memory stack, entirely separated from the `LLMClient`.

## Requirements
Implement an object-oriented Context stack in `src/tdd_harness/context.py`.

### 1. `ContextType` Enum
Define an enum mapping the conceptual context to its API role.
```python
class ContextType(Enum):
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
```

### 2. `Context` Data Class
A discrete block of memory.
- `id: str` (Unique identifier)
- `text: str` (The actual context text)
- `creation_time: datetime` 
- `context_type: ContextType`
- `metadata: dict[str, str]` (Optional key-value pairs, e.g., `{"filename": "app.py"}` for targeted retrieval).
- `token_count: int` (The token count for this specific block)
- `is_count_estimated: bool` (True if calculated via local heuristic/tiktoken; False if loaded from the persistent `.prompt-cache.yaml` or confirmed by the API).
- `is_compressible: bool` (Instance-level flag dictating if this block can be summarized or evicted).

*Logic:* Static blocks load their exact count from the persistent cache and set `is_compressible = False`. `COVERAGE_REPORT` also sets `is_compressible = False` because it is already a highly condensed markdown table. Dynamic blocks like `POST_MORTEM_SUMMARY` default to `is_compressible = True`.

### 3. `ContextBuilder` Class
A stateful stack manager. It MUST NOT make network calls.
- `add_context(new: Context) -> None`: Pushes a new context object to the stack.
- `remove_context(context_id: str) -> None`: Removes a context by ID.
- `replace_with_summary(context_ids: list[str], summary_text: str) -> None`: Removes the specified contexts and injects a new `Context` object of type `POST_MORTEM_SUMMARY`.
- `get_list_tokens(context_types: list[ContextType]) -> int`: Returns an instant O(1) sum of the cached `token_count` for the matching contexts.
- `get_context(context_types: list[ContextType] = None, metadata_filters: dict[str, str] = None) -> list[Context]`: Returns the raw `Context` objects, optionally filtering by metadata (e.g. `filename`).

**Handling Continuous Failures (Recursive Summarization):** 
If a Green phase fails repeatedly, the stack will accumulate multiple `ContextType.POST_MORTEM_SUMMARY` objects. To prevent token bloat, `POST_MORTEM_SUMMARY` objects must have `is_compressible = True`. When the budget is threatened, the `ContextBuilder` can select all existing summary blocks and pass them to `replace_with_summary` to collapse 15 old failure summaries into a single, cohesive "Meta-Summary."

### 4. LLM Adapter Serialization
The `ContextBuilder` must NOT format the final OpenAI JSON array. It just returns `list[Context]`. 
Update the `LLMClient` (or create a formatter strategy) to accept `list[Context]` and serialize it into the specific API format (`{"role": ..., "content": ...}`). This ensures that if we add OpenRouter or Anthropic later, the `ContextBuilder` remains completely agnostic to API schemas.
