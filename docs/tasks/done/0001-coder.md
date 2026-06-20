# Task: 0001-coder - Core Config Loader and Validation

## Context
Create the configuration models and loaders for `tdd-harness`. The project mandates the consistent use of YAML for all configuration files. 
The harness looks for a `.tdd-harness/` directory containing primary configuration files:
1. `tdd-harness.yaml`: Core system configuration (LLM endpoints, MCP extensions, loop guardrails).
2. `prompts/system_message.yaml`: Holds the system prompt payload, its SHA256 hash, and a dictionary of token counts for specific models.
3. `prompts/compression_prompt.yaml`: Holds the internal prompt used when context limits are reached.

## Target Files
- `src/tdd_harness/config.py`
- `tests/test_config.py`

## Instructions
- Implement a Directory Resolver that locates the `.tdd-harness/` directory based on the following fallback order:
  1. Specified project directory (if passed dynamically via arguments from the CLI).
  2. The current working directory (`./.tdd-harness/`).
  3. The user's home directory (`~/.tdd-harness/`).
- Define strict dataclasses or Pydantic models for both configuration schemas. The schemas MUST enforce these exact structures:
  - `TddHarnessConfig`:
    - `llm`: `provider` (str), `base_url` (str), `model` (str), `context_size` (int), `minimum_available_context` (int), `keep_turns` (int).
    - `harness`: `commands` (dict with required keys: `lint`, `test`, `coverage`), `coverage_threshold` (float), `max_uncovered_lines` (int).
    - `harness.anti_thrashing`: `max_duplicate_failures` (int), `max_window_failures` (int), `window_size` (int).
    - `mcp_servers`: list of dicts.
    - `extensions`: list of dicts.
  - `PromptConfig` (for files in `.tdd-harness/prompts/`):
    - `prompt`: str
- Implement a parser that exclusively reads `tdd-harness.yaml` from the `.tdd-harness/` directory.
- **The Prompt Class**: 
  - To support read-only VM mounts for the `.tdd-harness/` directory, prompt files must NEVER be written to.
  - Implement a `Prompt` class that parses read-only YAML files from `.tdd-harness/prompts/` (e.g., `system_message.yaml`, `compression_prompt.yaml`).
  - The `Prompt` class exposes methods: `token_size(model: str) -> int`, `filename() -> str`, `prompt() -> str`, and `hash() -> str`.
  - The token_size method should estimate the tokens if it doesn't have a known good value, only recording the value when it has an actual count from the LLM.
- **Cache Invalidation & State Tracking**: 
  - Mutable state (token caches) must be written exclusively to `.prompt-cache.yaml` in the project root.
  - On startup, the `Prompt` class computes the SHA256 hash of its text.
  - It looks up its entry in `.prompt-cache.yaml` under `prompt_caches.<prompt_name>.prompt_hash`.
  - If the calculated hash differs from the stored hash (or doesn't exist):
    - Clear the token cache for that prompt in `.prompt-cache.yaml` and save the new hash.
  - Implement an `update_token_size(model: str, count: int)` method on the `Prompt` class that safely updates the specific cache block in `.prompt-cache.yaml`.
- Validate the commands list (ensure it is non-empty, contains required scripts).

## Success Criteria
- Config directory resolver accurately hits the 3 fallback locations.
- Both configs parsed successfully match their schemas.
- Modifying the prompt text successfully invalidates the token cache and updates the hash on the next run.
- `update_token_count()` successfully adds the token count and persists it.
- `ruamel.yaml` correctly preserves the `|` multiline syntax for the prompt during saves.
- Unit tests written in `tests/test_config.py` cover edge cases.
