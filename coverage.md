# Test Coverage Report

- **Date:** 2026-06-22 21:13:26
- **Branch:** `task/0037`
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
| src/tdd_harness/cli.py                   | 112 | 107 | 95.54% | 117-118, 137, 166, 224 |
| src/tdd_harness/config.py                | 84 | 72 | 85.71% | 91, 113, 129, 137-144, 162 |
| src/tdd_harness/context.py               | 68 | 65 | 95.59% | 56, 135-136 |
| src/tdd_harness/controller.py            | 526 | 447 | 84.98% | 117, 139-142, 169-170, 199, 229, 261, 270-273, 276-280, 282-283, 290, 315-318, 320-321, 345, 351, 360-361, 388, 393, 395, 398, 434, 439-440, 472-477, 488, 509-510, 521-522, 555-556, 572-573, 584-585, 629, 645-646, 656, 683, 685-691, 697-698, 724, 738, 758, 767, 789-790, 795, 803-804 |
| src/tdd_harness/coverage_parser.py       | 53 | 50 | 94.34% | 50, 53-54 |
| src/tdd_harness/exceptions.py            | 8 | 8 | 100.00% |  |
| src/tdd_harness/llm.py                   | 108 | 105 | 97.22% | 116-117, 179 |
| src/tdd_harness/mcp_client.py            | 72 | 66 | 91.67% | 38-39, 77, 105-107 |
| src/tdd_harness/models/__init__.py       | 2 | 2 | 100.00% |  |
| src/tdd_harness/models/tool.py           | 10 | 10 | 100.00% |  |
| src/tdd_harness/phase.py                 | 9 | 9 | 100.00% |  |
| src/tdd_harness/prompt.py                | 49 | 49 | 100.00% |  |
| src/tdd_harness/registry.py              | 150 | 149 | 99.33% | 128 |
| src/tdd_harness/runner.py                | 140 | 124 | 88.57% | 83, 85, 87, 105, 117-120, 252, 276-279, 283, 292, 303 |
| src/tdd_harness/security.py              | 43 | 43 | 100.00% |  |
| src/tdd_harness/sub_agents.py            | 43 | 43 | 100.00% |  |
| src/tdd_harness/task_loader.py           | 68 | 65 | 95.59% | 49, 97-98 |
| src/tdd_harness/tool_schemas.py          | 4 | 4 | 100.00% |  |
| src/tdd_harness/tracker.py               | 42 | 40 | 95.24% | 87, 107 |
| src/tdd_harness/utils.py                 | 36 | 35 | 97.22% | 30 |
| tests/conftest.py                        | 7 | 7 | 100.00% |  |
| tests/test_cli.py                        | 213 | 211 | 99.06% | 89-90 |
| tests/test_config.py                     | 40 | 40 | 100.00% |  |
| tests/test_context.py                    | 23 | 23 | 100.00% |  |
| tests/test_controller.py                 | 391 | 389 | 99.49% | 19, 586 |
| tests/test_coverage_parser.py            | 58 | 58 | 100.00% |  |
| tests/test_lcov_adapter.py               | 20 | 20 | 100.00% |  |
| tests/test_llm.py                        | 193 | 193 | 100.00% |  |
| tests/test_mcp_client.py                 | 122 | 122 | 100.00% |  |
| tests/test_prompt.py                     | 60 | 60 | 100.00% |  |
| tests/test_pytest_adapter.py             | 36 | 36 | 100.00% |  |
| tests/test_registry.py                   | 127 | 125 | 98.43% | 40, 90 |
| tests/test_ruff_adapter.py               | 31 | 31 | 100.00% |  |
| tests/test_runner.py                     | 83 | 82 | 98.80% | 75 |
| tests/test_security.py                   | 68 | 68 | 100.00% |  |
| tests/test_sub_agents.py                 | 68 | 68 | 100.00% |  |
| tests/test_task_loader.py                | 106 | 105 | 99.06% | 56 |
| tests/test_tracker.py                    | 58 | 58 | 100.00% |  |
| tests/test_utils.py                      | 54 | 54 | 100.00% |  |
| **LCOV Aggregated Language Counts** | 3499 | 3339 | 95.43% | |

