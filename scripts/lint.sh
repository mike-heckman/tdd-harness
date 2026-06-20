#!/usr/bin/env bash
#
# NOTE: This script is hard-linked to the ai-project-configuration/scripts/lint.sh script. 
# Do not modify this file. If an override is needed, create a _local_lint.sh
# script in the same directory with the desired changes. 
# Last edit: 2026-04-10 by Mike
#

set -e
set -o pipefail


# Heuristic check: Look for the root anchor (e.g., .git, package.json, or GEMINI.md)
# This walks up the directory tree until it finds a marker.
get_project_root() {
    local dir="$1"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.git" ]]; then
            echo "$dir"
            return
        fi
        dir="$(dirname "$dir")"
    done
    # Fallback to script's parent directory if no marker found
    echo "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
}

# Use script directory as the starting point for root discovery to ensure it works even if run from a different CWD.
export PROJECT_ROOT="${PROJECT_ROOT:-${VSCODE_CWD:-$(get_project_root "$PWD")}}"
[ -f "${PROJECT_ROOT}/.languages" ] && source "${PROJECT_ROOT}/.languages"

# Make sure the logging directory exists
if [ ! -d "${PROJECT_ROOT}/logs" ]; then
    mkdir -p "${PROJECT_ROOT}/logs"
fi

# Clear existing log if it exists
export LINT_LOG="${PROJECT_ROOT}/logs/lint.log"
if [ -f "${LINT_LOG}" ]; then
    echo "Clearing existing lint log at ${LINT_LOG}" 
    rm -f "${LINT_LOG}"
fi

run_linter() {
    local lang="$1"
    local tool="$2"
    local cmd="$3"
    
    echo "=====================================" | tee -a "${LINT_LOG}"
    echo "Running ${lang} ${tool}..." | tee -a "${LINT_LOG}"
    
    set +e
    eval "$cmd" 2>&1 | tee -a "${LINT_LOG}"
    local exit_code=${PIPESTATUS[0]}
    set -e
    
    if [ $exit_code -eq 0 ]; then
        echo "[PASS] ${tool}" | tee -a "${LINT_LOG}"
        return 0
    else
        echo "[FAIL] ${tool}" | tee -a "${LINT_LOG}"
        return $exit_code
    fi
}
export -f run_linter

# Set the PROJECT_ROOT and language flags for the local override script if it exists. 
# This allows the local script to have the same context.
if [ -x "${PROJECT_ROOT}/scripts/_local_lint.sh" ]; then
    echo "Running local override script..."
    exec "${PROJECT_ROOT}/scripts/_local_lint.sh"
fi

if [[ "${HAS_PY}" == "true" ]]; then
    if [ -x "${PROJECT_ROOT}/scripts/lint-py.sh" ]; then
        # Run the Python linting script, which is modularized for clarity.
        "${PROJECT_ROOT}/scripts/lint-py.sh"
    else
        echo "Python lint script not found or not executable at ${PROJECT_ROOT}/scripts/lint-py.sh, even though HAS_PY=${HAS_PY}. Aborting."
        exit 1
    fi    
fi

# Configuration files (.eslint.config.js, .prettierrc, .tsconfig.json) 
# should already be present in the project root.

if [[ "${HAS_TS}" == "true" ]]; then
    if [ -x "${PROJECT_ROOT}/scripts/lint-ts.sh" ]; then
        # Run the TypeScript linting script, which is modularized for clarity.
        "${PROJECT_ROOT}/scripts/lint-ts.sh"
    else
        echo "Typescript lint script not found or not executable at ${PROJECT_ROOT}/scripts/lint-ts.sh, even though HAS_TS=${HAS_TS}. Aborting."
        exit 1    
    fi
fi

for file in docs/tasks/reports/success_report_test-*.md; do
    if [ -f "$file" ]; then
        rm -f "$file"
    fi
done

for dir in .tdd-harness/backups/test-*; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
    fi
done

echo "Completed successfully at $(date)" | tee -a "${LINT_LOG}"
