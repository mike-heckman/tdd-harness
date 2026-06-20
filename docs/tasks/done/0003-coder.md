# Task: 0003-coder - LLM Client Adapter and Context Compressor

## Context
Implement the client adapter layer to interact with the LLM. It must support OpenAI with custom connection points and automatic context compression when remaining context falls below a configured minimum. It also handles capturing and caching the system message baseline token count per-model.

## Target Files
- `src/tdd_harness/llm.py`
- `tests/test_llm.py`

## Instructions
- Integrate the `openai` Python SDK to communicate with OpenAI-compatible endpoints.
- Support API configuration (api_key, base_url, model, context_size, minimum_available_context, keep_turns).
- **System Token Baseline Caching**:
  - Read the system message using the `Prompt` class (via Config Loader). If `prompt.token_size(model)` returns a value, use it.
  - On the first successful LLM call of a session, if the token size returned `None`, extract the `usage.prompt_tokens` (or equivalent metric) from the API response payload.
  - Calculate the system message's token footprint and call `prompt.update_token_size(model, count)` to persist the result to `.prompt-cache.yaml`.
- **Context Compression Protocol**:
  - Calculate remaining context using the cached system baseline + subsequent request estimations/stats.
  - If remaining context <= `minimum_available_context`:
    - Extract the system message, current task description, and the last `keep_turns` request/responses.
    - Send the older messages to the LLM to compress/summarize using the prompt loaded from `.tdd-harness/prompts/compression_prompt.yaml` (provided by the Config Loader).
    - Replace the compressed messages in the chat history with a single summary message.

## Success Criteria
- Mock tests simulate successful calls and accurate baseline token extraction.
- The `system_message.yaml` is properly updated with new token sizes for unknown models.
- When remaining context drops below the threshold, compression is triggered and the history is correctly rebuilt.
- Unit tests written in `tests/test_llm.py` cover threshold triggering and baseline extraction.
