---
id: '0012'
title: Post-Mortem Summarization & Context Conservation
success_criteria:
- 'Update the `stage_implementation` (and `stage_test_implementation`) execution logic:
  if the tool runs `pytest` or `ruff` and encounters a failure, it must trigger a
  secondary, internal LLM API call.'
- The secondary LLM call should be prompted to analyze the raw traceback and broken
  code. It must return a 2-3 sentence technical summary of the root cause AND a specific,
  actionable suggestion for what the primary agent should do differently to fix it
  (the "Post-Mortem Summary & Guidance").
- The harness must then **revert** the file to its pre-staged state by restoring it
  from a crash-safe `.tdd-harness/backups/<instance_id>/` copy created prior to the
  task's first modification.
- The harness must discard the raw traceback and chronological chat history of the
  failure to save tokens.
- The raw error and bad code must be completely wiped from the context window, and only
  the "Post-Mortem Summary & Guidance" is injected into the primary agent's next prompt.
- Ensure the primary agent context explicitly includes a "Past Failure Summaries"
  section.
dependencies:
  prod: []
  dev: []
---
# Unit of Work: Post-Mortem Summarization & Context Conservation

## Context
When the LLM fails a phase (e.g., tests fail in the Green phase), injecting the full raw traceback and keeping the broken code in the context window rapidly depletes the token budget and distracts the agent. We need to implement Post-Mortem Summarization to condense failures into concise, actionable summaries.
