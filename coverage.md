# Test Coverage Report

- **Date:** 2026-06-22 16:01:50
- **Branch:** `task/0031`
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
| src/tdd_harness/cli.py                   | 104 | 99 | 95.19% | 114-115, 136, 161, 216 |
| src/tdd_harness/config.py                | 89 | 77 | 86.52% | 96, 118, 134, 142-149, 167 |
| src/tdd_harness/context.py               | 74 | 71 | 95.95% | 56, 146-147 |
| src/tdd_harness/controller.py            | 627 | 507 | 80.86% | 179-182, 209-210, 239, 291, 300-303, 306-310, 312-313, 330, 338-341, 343-344, 368, 377-378, 405, 410, 415, 418, 441-444, 454-455, 457-458, 460-461, 463-468, 471-472, 481, 495, 504, 508-509, 512, 516, 519, 522, 528-530, 533, 535, 537-543, 545-549, 585, 590-591, 623-628, 639, 660-661, 672-673, 701-702, 718-719, 730-731, 770, 786-787, 797, 819, 821-827, 833-834, 860, 874, 894, 903, 925-926, 931, 939-940 |
| src/tdd_harness/coverage_parser.py       | 53 | 50 | 94.34% | 50, 53-54 |
| src/tdd_harness/llm.py                   | 107 | 104 | 97.20% | 116-117, 179 |
| src/tdd_harness/mcp_client.py            | 64 | 55 | 85.94% | 36-37, 67, 95-97, 116-118 |
| src/tdd_harness/models/__init__.py       | 2 | 2 | 100.00% |  |
| src/tdd_harness/models/tool.py           | 10 | 10 | 100.00% |  |
| src/tdd_harness/prompt.py                | 49 | 49 | 100.00% |  |
| src/tdd_harness/registry.py              | 150 | 149 | 99.33% | 128 |
| src/tdd_harness/runner.py                | 140 | 124 | 88.57% | 83, 85, 87, 105, 117-120, 252, 276-279, 283, 292, 303 |
| src/tdd_harness/sub_agents.py            | 43 | 43 | 100.00% |  |
| src/tdd_harness/tool_schemas.py          | 4 | 4 | 100.00% |  |
| src/tdd_harness/tracker.py               | 41 | 39 | 95.12% | 87, 107 |
| tests/conftest.py                        | 7 | 7 | 100.00% |  |
| tests/test_cli.py                        | 181 | 179 | 98.90% | 89-90 |
| tests/test_config.py                     | 40 | 40 | 100.00% |  |
| tests/test_context.py                    | 23 | 23 | 100.00% |  |
| tests/test_controller.py                 | 440 | 438 | 99.55% | 17, 426 |
| tests/test_coverage_parser.py            | 58 | 58 | 100.00% |  |
| tests/test_lcov_adapter.py               | 20 | 20 | 100.00% |  |
| tests/test_llm.py                        | 186 | 186 | 100.00% |  |
| tests/test_mcp_client.py                 | 99 | 99 | 100.00% |  |
| tests/test_prompt.py                     | 60 | 60 | 100.00% |  |
| tests/test_pytest_adapter.py             | 36 | 36 | 100.00% |  |
| tests/test_registry.py                   | 127 | 125 | 98.43% | 40, 90 |
| tests/test_ruff_adapter.py               | 31 | 31 | 100.00% |  |
| tests/test_runner.py                     | 83 | 82 | 98.80% | 75 |
| tests/test_sub_agents.py                 | 68 | 68 | 100.00% |  |
| tests/test_tracker.py                    | 58 | 58 | 100.00% |  |
| **LCOV Aggregated Language Counts** | 3188 | 2989 | 93.76% | |

