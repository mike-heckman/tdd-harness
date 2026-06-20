# TDD Harness Task Schema

This document defines the strict API contract for Task files processed by the `tdd-harness`. The Harness is persona-agnostic; it will process files placed in `docs/tasks/ready/` that conform to this schema.

## Filename Constraints
- Files MUST use the `.md` suffix.
- Files MUST have internally unique names within the task system.
- The Harness processes the `ready/` directory in **asciibetical order**. Files should use an ever-increasing prefix (e.g., sequential padding `0001-`, `0002-` or `UUIDv7`) to ensure they execute in the correct deterministic dependency order.

If a file fails validation during the Amber phase, it will be moved to `docs/tasks/error/` and a corresponding `.error.log` file will be generated containing the validation feedback. The original task file is never modified by the Harness.

## Schema Definition

### YAML Frontmatter
The file MUST begin with valid YAML frontmatter.
- `id` (string, required): A unique identifier for the task.
- `title` (string, required): A brief description of the task.
- `dependencies` (object, optional): External libraries required by the task.
  - `prod` (list of strings): Production dependencies.
  - `dev` (list of strings): Development/Testing dependencies.
- `target_files` (list of strings, optional): Explicit filepaths the task is expected to modify (can be used to narrow context or pre-warm the MCP index).
- `success_criteria` (list of strings, required): An explicit list of testable requirements (Definition of Done) that the task must mathematically satisfy.

### Markdown Body
The markdown body is reserved for qualitative, unstructured context.
- `## Context`: Background architectural information, edge cases, and design rationale.

## Output Contract (Reports)
When the execution agent completes or fails a task, it uses the native `success(message)` or `abort(reason)` tools. The Harness captures these LLM-generated messages and writes them to `./docs/tasks/reports/<task_id>.md`. External personas (Architect, Librarian) should monitor this `reports/` directory to review the agent's implementation notes or roadblock explanations.

---

## Example Task File

```markdown
---
id: "0016"
title: "Implement API Rate Limiter"
dependencies:
  prod:
    - "redis"
  dev:
    - "fakeredis"
target_files:
  - "src/middleware/rate_limit.py"
success_criteria:
  - "The rate limiter must allow 100 requests per minute per IP."
  - "Requests exceeding the limit must return HTTP 429."
---
# Unit of Work: Implement API Rate Limiter

## Context
We need to prevent API abuse by implementing a sliding-window rate limiter using Redis. The Redis connection should be managed via a dependency injection pattern.
```
