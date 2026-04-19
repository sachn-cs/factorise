#!/usr/bin/env bash

# Factorise Cleanup Script
#
# Safely removes local build artifacts, caches, and temporary files.
# This script is idempotent and guards against accidental deletion
# of source code or user data.
#
# Usage: ./cleanup.sh

set -euo pipefail

# --- Configuration ---
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define explicit paths relative to root for safety
TARGET_DIRECTORIES=(
    ".benchmarks"
    ".hypothesis"
    ".mypy_cache"
    ".pytest_cache"
    ".ruff_cache"
    ".venv"
    "dist"
    "build"
)

TARGET_FILES=(
    ".coverage"
)

# --- Helpers ---
log() {
    echo -e "\033[1;34m[CLEANUP]\033[0m $1"
}

remove_if_exists() {
    local path="$1"
    if [[ -e "$path" ]]; then
        log "Removing $path..."
        rm -rf "$path"
    else
        log "Skipped $path (not found)"
    fi
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Execution ---
cd "$PROJECT_ROOT"

log "Starting repository cleanup in $PROJECT_ROOT"

# 1. Remove explicit directories
for dir in "${TARGET_DIRECTORIES[@]}"; do
    remove_if_exists "$dir"
done

# 2. Uninstall pre-commit hooks if pre-commit is available
if [[ -d ".git/hooks" ]]; then
    # Try using pre-commit if it's in the PATH or venv (before venv is gone)
    if command_exists pre-commit; then
        log "Uninstalling pre-commit hooks..."
        pre-commit uninstall >/dev/null 2>&1 || true
    elif [[ -x "$PROJECT_ROOT/.venv/bin/pre-commit" ]]; then
        log "Uninstalling pre-commit hooks via venv..."
        "$PROJECT_ROOT/.venv/bin/pre-commit" uninstall >/dev/null 2>&1 || true
    fi

    # Manual cleanup as a fallback to ensure no broken hooks remain
    if [[ -f ".git/hooks/pre-commit" ]]; then
        log "Force removing pre-commit hook..."
        rm -f ".git/hooks/pre-commit"
    fi
fi

# 3. Remove explicit files
for file in "${TARGET_FILES[@]}"; do
    # Handle coverage patterns (e.g., .coverage.hostname.pid)
    if [[ "$file" == ".coverage" ]]; then
        # Find and remove all coverage-related files safely
        find . -maxdepth 1 -name ".coverage*" -exec rm -f {} +
        log "Removed .coverage data files"
    else
        remove_if_exists "$file"
    fi
done

# 3. Recursive cleanup of __pycache__ and egg-info
log "Scanning for recursive artifacts (__pycache__, *.egg-info)..."

# Safely find and remove directories
find . -type d \( -name "__pycache__" -o -name "*.egg-info" \) -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true

log "Cleanup complete! Repository is in a fresh state."
