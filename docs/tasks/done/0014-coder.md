---
id: '0014'
title: Review Sub-Agent (`success` Gate)
success_criteria:
- Update the execution logic of the native `success()` tool.
- When `success()` is called and local metrics (pytest/ruff/lcov) pass, instantiate
  a secondary, stateless LLM client (the Review Sub-Agent).
- The Sub-Agent must be prompted as a Senior Code Reviewer. It is provided with the
  original `Task File` (full DoD), a unified `diff` of the task's changes (generated
  by comparing the working files against their `.tdd-harness/backups/<instance_id>/`
  copies), and a list of modified files.
- The Sub-Agent must be given access to read-only `jcodemunch` tools (`get_file_content`,
  `get_symbol_source`) so it can investigate the full files if the diff lacks context.
- 'The Sub-Agent must return a structured response: `APPROVE` or `REJECT: <specific
  critique>`.'
- If `APPROVE`, the `success()` tool officially advances the state machine.
- If `REJECT`, the `success()` tool returns a failure state to the primary agent,
  injecting the Reviewer's specific critique into the context payload so the primary
  agent can address the missing requirements without losing its flow.
dependencies:
  prod: []
  dev: []
---
# Unit of Work: Review Sub-Agent (`success` Gate)

## Context
When the primary agent is deep in the implementation loop, it may hallucinate completion when the tests compile but the underlying business logic in the Definition of Done (DoD) is unmet. We need a stateless Review Sub-Agent to act as a final judge before the `success()` tool officially advances the task.
