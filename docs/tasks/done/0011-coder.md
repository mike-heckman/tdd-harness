---
id: '0011'
title: Progressive Errors in Native Tools
success_criteria:
- Update the initialization logic of native tools (e.g., `run_lint`, `run_test`, `run_coverage`
  in `tools.py` or `runner.py`) to accept their specific configuration block mapped
  from `.tdd-harness/tools/python.yaml`.
- 'Update the execution wrapper of native tools to accept `previous_failures: int
  = 0`.'
- The native tool must internally use its provided configuration and the failure count
  to format and return progressively verbose error payloads matching the hints defined
  in its YAML block.
- Write unit tests ensuring that native tools correctly format error payloads using
  injected configurations based on failure counts.
dependencies:
  prod: []
  dev: []
---
# Unit of Work: Progressive Errors in Native Tools

## Context
Native tools must now utilize the injected `previous_failures` parameter to escalate their error verbosity dynamically.
