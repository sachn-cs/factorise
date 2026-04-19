#!/usr/bin/env bash

# Factorise Development Setup Script
#
# Standard entry point for setting up a local development environment.
# Performs virtual environment initialization, dependency installation,
# and tool configuration (e.g., pre-commit hooks).
#
# Usage: ./setup.sh

set -euo pipefail

# --- Configuration ---
PYTHON_MIN_VERSION="3.10"
VENV_DIR=".venv"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Helpers ---
log() {
    echo -e "\033[1;32m[SETUP]\033[0m $1"
}

warn() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1" >&2
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_python_version() {
    local python_bin="$1"
    local version
    version=$($python_bin -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    # Simple version comparison
    if [[ $(echo -e "$version\n$PYTHON_MIN_VERSION" | sort -V | head -n1) == "$PYTHON_MIN_VERSION" ]]; then
        return 0
    else
        return 1
    fi
}

# --- Detection ---
cd "$PROJECT_ROOT"

log "Detected project root: $PROJECT_ROOT"

# Find a suitable Python binary
PYTHON_CMD=""
# Check standard PATH first, then common installation directories
SEARCH_PATHS=("" "/opt/homebrew/bin" "/usr/local/bin" "/opt/anaconda3/bin")

for path in "${SEARCH_PATHS[@]}"; do
    for cmd_name in python3.12 python3.11 python3.10 python3; do
        if [[ -n "$path" ]]; then
            cmd="$path/$cmd_name"
        else
            cmd="$cmd_name"
        fi

        if command_exists "$cmd"; then
            if check_python_version "$cmd"; then
                PYTHON_CMD="$cmd"
                break 2
            fi
        fi
    done
done

if [[ -z "$PYTHON_CMD" ]]; then
    error "Python $PYTHON_MIN_VERSION+ is required but not found. Please install it to continue."
fi

log "Using $(which "$PYTHON_CMD") ($($PYTHON_CMD --version))"

# --- Virtual Environment ---
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtual environment in $VENV_DIR..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
else
    log "Virtual environment already exists in $VENV_DIR."
fi

# Determine venv python path
VENV_PYTHON="$PROJECT_ROOT/$VENV_DIR/bin/python3"
VENV_PIP="$PROJECT_ROOT/$VENV_DIR/bin/pip"

# --- Dependencies ---
log "Installing/updating project dependencies (editable mode)..."
"$VENV_PIP" install -q --upgrade pip
"$VENV_PIP" install -e ".[dev]"

# --- Pre-commit Hooks ---
if [[ -f ".pre-commit-config.yaml" ]]; then
    if [[ -x "$PROJECT_ROOT/$VENV_DIR/bin/pre-commit" ]]; then
        log "Installing pre-commit hooks..."
        "$PROJECT_ROOT/$VENV_DIR/bin/pre-commit" install
    else
        warn "pre-commit found in config but not in .venv. Skipping hook installation."
    fi
fi

# --- Optional Tooling Hints ---
if ! command_exists "just"; then
    warn "'just' task runner not found. We recommend installing it: https://github.com/casey/just"
fi

log "Setup complete! You can now activate the environment with:"
echo -e "\033[1;34m    source $VENV_DIR/bin/activate\033[0m"
