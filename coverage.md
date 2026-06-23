# Test Coverage Report

- **Date:** 2026-06-22 22:01:33
- **Branch:** `task/0042`
- **Status:** PASSED

### LCOV Aggregated

| File | Lines | Covered | % Coverage | Missing |
| :--- | ---: | ---: | ---: | :--- |
| src/tdd_harness/__init__.py              | 0 | 0 | 0.00% |  |
| src/tdd_harness/adapters/__init__.py     | 2 | 2 | 100.00% |  |
| src/tdd_harness/adapters/base.py         | 23 | 18 | 78.26% | 23, 42, 61, 80, 93 |
| src/tdd_harness/adapters/lcov_adapter.py | 18 | 14 | 77.78% | 23, 33, 44-45 |
| src/tdd_harness/adapters/pytest_adapter.py | 42 | 36 | 85.71% | 36-37, 51, 66-68 |
| src/tdd_harness/adapters/ruff_adapter.py | 29 | 26 | 89.66% | 32, 53-54 |
| src/tdd_harness/cli.py                   | 108 | 104 | 96.30% | 117-118, 137, 219 |
| src/tdd_harness/config.py                | 84 | 71 | 84.52% | 36, 95, 117, 133, 141-148, 166 |
| src/tdd_harness/context.py               | 68 | 65 | 95.59% | 56, 135-136 |
| src/tdd_harness/controller.py            | 449 | 386 | 85.97% | 118, 140-143, 170-171, 200, 230, 262, 271-274, 277-281, 283-284, 291, 316-319, 321-322, 346, 352, 361-362, 389, 394, 396, 399, 435, 440-441, 473-478, 489, 502-503, 545, 570, 608, 610-616, 622-623, 639, 659, 669 |
| src/tdd_harness/coverage_parser.py       | 53 | 50 | 94.34% | 50, 53-54 |
| src/tdd_harness/exceptions.py            | 8 | 8 | 100.00% |  |
| src/tdd_harness/llm.py                   | 117 | 114 | 97.44% | 129-130, 192 |
| src/tdd_harness/mcp_client.py            | 77 | 71 | 92.21% | 39-40, 95, 123-125 |
| src/tdd_harness/models/__init__.py       | 2 | 2 | 100.00% |  |
| src/tdd_harness/models/tool.py           | 10 | 10 | 100.00% |  |
| src/tdd_harness/phase.py                 | 9 | 9 | 100.00% |  |
| src/tdd_harness/prompt.py                | 49 | 49 | 100.00% |  |
| src/tdd_harness/protocols.py             | 10 | 10 | 100.00% |  |
| src/tdd_harness/registry.py              | 151 | 150 | 99.34% | 130 |
| src/tdd_harness/runner.py                | 140 | 124 | 88.57% | 83, 85, 87, 105, 117-120, 252, 276-279, 283, 292, 303 |
| src/tdd_harness/security.py              | 43 | 43 | 100.00% |  |
| src/tdd_harness/sub_agents.py            | 43 | 43 | 100.00% |  |
| src/tdd_harness/task_loader.py           | 68 | 65 | 95.59% | 49, 97-98 |
| src/tdd_harness/tool_schemas.py          | 4 | 4 | 100.00% |  |
| src/tdd_harness/tracker.py               | 42 | 40 | 95.24% | 87, 107 |
| src/tdd_harness/utils.py                 | 36 | 35 | 97.22% | 30 |
| tests/conftest.py                        | 12 | 12 | 100.00% |  |
| tests/test_cli.py                        | 213 | 211 | 99.06% | 89-90 |
| tests/test_config.py                     | 40 | 40 | 100.00% |  |
| tests/test_context.py                    | 23 | 23 | 100.00% |  |
| tests/test_controller.py                 | 422 | 420 | 99.53% | 19, 586 |
| tests/test_coverage_parser.py            | 58 | 58 | 100.00% |  |
| tests/test_lcov_adapter.py               | 20 | 20 | 100.00% |  |
| tests/test_llm.py                        | 193 | 193 | 100.00% |  |
| tests/test_mcp_client.py                 | 137 | 137 | 100.00% |  |
| tests/test_prompt.py                     | 60 | 60 | 100.00% |  |
| tests/test_pytest_adapter.py             | 36 | 36 | 100.00% |  |
| tests/test_registry.py                   | 127 | 125 | 98.43% | 40, 90 |
| tests/test_ruff_adapter.py               | 31 | 31 | 100.00% |  |
| tests/test_runner.py                     | 83 | 82 | 98.80% | 75 |
| tests/test_security.py                   | 68 | 68 | 100.00% |  |
| tests/test_sub_agents.py                 | 68 | 68 | 100.00% |  |
| tests/test_task_loader.py                | 106 | 105 | 99.06% | 56 |
| tests/test_tool_schemas.py               | 10 | 10 | 100.00% |  |
| tests/test_tracker.py                    | 58 | 58 | 100.00% |  |
| tests/test_utils.py                      | 54 | 54 | 100.00% |  |
| **LCOV Aggregated Language Counts** | 3504 | 3360 | 95.89% | |

