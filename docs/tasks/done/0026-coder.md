---
id: "0026"
title: "Integrate AntiThrashingTracker into Controller & Refine Registry Schema Generation"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
  - "src/tdd_harness/registry.py"
success_criteria:
  - "The `TDDLoopController.__init__` must instantiate an `AntiThrashingTracker` using the `anti_thrashing` config values from `config.harness` and pass it to the `ToolRegistry`."
  - "Every tool dispatch in the phase driver loops (Blue, Red, Green, Magenta) must call `tracker.record_tool_call()` with the `ToolCall` and `ToolCallResponse`."
  - "After each tool dispatch, the controller must check `tracker.should_abort()` and terminate the loop with a dirty exit if True, per SDD §5."
  - "Replace the placeholder schema generation in `ToolRegistry.register_python_tool()` (line 179: `properties[param_name] = {\"type\": \"string\"}`) with proper type inference from Python type annotations (str -> string, int -> integer, float -> number, bool -> boolean, list -> array)."
  - "Add or update unit tests covering tracker integration in the controller and accurate schema generation from type annotations."
---
# Unit of Work: Integrate AntiThrashingTracker into Controller & Refine Registry Schema Generation

## Context
The `AntiThrashingTracker` is fully implemented in `tracker.py` with rolling window detection, duplicate failure tracking, and per-tool failure counts. However, it is never instantiated or used by the `TDDLoopController`. The `ToolRegistry` also has a placeholder where all parameter types default to `"string"` regardless of their Python type annotations, which produces inaccurate OpenAI function schemas.
