---
id: "0025"
title: "Refactor Controller: Extract Sub-Agents & Consolidate LLMClient"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
  - "src/tdd_harness/sub_agents.py"
success_criteria:
  - "Create a new module `src/tdd_harness/sub_agents.py` to house the sub-agent logic."
  - "Extract the Review Sub-Agent (`success` logic), Post-Mortem Sub-Agent (`_generate_post_mortem`), and Research Sub-Agent (`ask_researcher`) out of `TDDLoopController` and into `sub_agents.py`."
  - "Remove all 3 raw `AsyncOpenAI` instantiations currently hardcoded in `controller.py`."
  - "Update the extracted sub-agents to accept and utilize the shared `LLMClient` instance (implemented in Task 0024)."
  - "Ensure the sub-agents accept a `Prompt` instance (or load from yaml) to eliminate the hardcoded prompt strings previously embedded directly in the python code."
  - "Update `TDDLoopController` to delegate to these cleanly separated sub-agent classes/functions, significantly reducing its class size."
  - "Add unit tests for the extracted sub-agents in `tests/test_sub_agents.py`."
---
# Unit of Work: Refactor Controller: Extract Sub-Agents & Consolidate LLMClient

## Context
The `TDDLoopController` class has accumulated significant technical debt. It currently contains multiple redundant `AsyncOpenAI` initializations, embeds large hardcoded prompt strings directly in the python logic, and has grown to a size that makes unit testing difficult. Before implementing the complex Phase Driver loops (Tasks 0026+), we must extract the standalone sub-agents (Review, Post-Mortem, Research) into their own module and consolidate all LLM interactions through the standard `LLMClient` and `Prompt` config systems.
