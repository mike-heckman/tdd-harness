---
id: 0009
title: Magenta Phase LCOV Coverage Looping
success_criteria:
- Adapt the existing `generate-unified-coverage.py` concept to output standard `lcov`.
- Create a parser that reads the `lcov` file and isolates files with missing coverage.
- Implement a sub-loop in the Magenta phase that iterates through each file individually,
  passing the specific missing line numbers to the LLM.
- Halt the harness and alert the human if the LLM fails to increase coverage for a
  file after X attempts (add a stub note in the code for future dynamic handling).
dependencies:
  prod: []
  dev: []
---
# Unit of Work: Magenta Phase LCOV Coverage Looping

## Context
The Magenta phase uses `lcov` coverage reports to ensure target coverage is met by looping file-by-file. See files in ./docs/phases/ for additional detail.
