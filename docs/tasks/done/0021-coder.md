---
id: "0021"
title: "Implement tdd-harness init command"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/cli.py"
success_criteria:
  - "Add support in cli.py for an 'init' subcommand or positional argument."
  - "When 'init' is invoked, create a default '.tdd-harness' directory in the project root."
  - "Write a default 'config.yaml' inside '.tdd-harness/' matching the schema in the software design document."
  - "Write default system_message.yaml and compression_prompt.yaml files in '.tdd-harness/prompts/'."
  - "Ensure CLI parsing does not throw errors when positional or unknown arguments are passed."
  - "Add unit tests in tests/test_cli.py to verify init command functionality and directory creation."
---
# Unit of Work: Implement tdd-harness init command

## Context
The CLI prints a warning message asking the user to run `tdd-harness init` when `.tdd-harness/` is not found, but the command itself is not implemented. We need to implement it to allow easy initialization of new projects.
