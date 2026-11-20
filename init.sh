#!/usr/bin/env bash
# One command: make .venv, install the project with dev tools, run every test offline.
set -euo pipefail
cd "$(dirname "$0")"
if command -v uv >/dev/null 2>&1; then
  [ -d .venv ] || uv venv -q .venv
  uv pip install -q --python .venv/bin/python -e ".[dev]"
else
  [ -d .venv ] || python3 -m venv .venv
  .venv/bin/pip install -q -e ".[dev]"
fi
.venv/bin/ruff check src tests scripts
.venv/bin/ruff check --select S src scripts
.venv/bin/python -m pytest -q
.venv/bin/census self-check
echo "init.sh: all checks passed"
