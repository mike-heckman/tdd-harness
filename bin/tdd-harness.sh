#!/bin/bash

# This is the primary executable for the tdd-harness.
# It sets up the Python environment and executes the main module.

set -e

# Find the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PROJECT_ROOT

# Activate the virtual environment if it exists
if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
    source "${PROJECT_ROOT}/.venv/bin/activate"
fi

# Run the main Python module
exec python "${PROJECT_ROOT}/src/tdd_harness/cli.py" "$@"