---
id: "0033"
title: "Performance Review: LLM Call Efficiency & Adapter Orchestration"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
  - "src/tdd_harness/runner.py"
  - "src/tdd_harness/llm.py"
success_criteria:
  - "Profile the number of LLM API calls per phase and identify any redundant invocations (e.g., duplicate post-mortem calls, unnecessary compression triggers)."
  - "Analyze the `orchestrate_global()` function for unnecessary subprocess spawning when coverage data is already available."
  - "Verify the `ContextBuilder` token arithmetic prevents context deadlocks per SDD §5 (static token size check before any LLM call)."
  - "Measure and report the overhead of the `AntiThrashingTracker` hash computation per tool call."
  - "Document findings in a performance audit report at `docs/tasks/reports/0032-performance-audit.md`."
---
# Unit of Work: Performance Review: LLM Call Efficiency & Adapter Orchestration

## Context
With the full TDD loop now invoking multiple LLM calls per phase (primary agent + post-mortem + compression + reviewer sub-agent + researcher sub-agent), there is risk of excessive token expenditure and redundant subprocess invocations. A performance audit is required per Architect backlog policy.
