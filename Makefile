.PHONY: test lint self-check report eval

# A fresh clone has no .venv yet. Build it on first use so `make test` works
# without running ./init.sh first.
.venv/bin/python:
	python3 -m venv .venv
	.venv/bin/pip install -q -e ".[dev]"

test: .venv/bin/python
	.venv/bin/python -m pytest -q

lint: .venv/bin/python
	.venv/bin/ruff check src tests scripts

self-check: .venv/bin/python
	.venv/bin/census self-check

eval: .venv/bin/python
	.venv/bin/census drift-eval

report: .venv/bin/python
	.venv/bin/census analyze
	.venv/bin/census report
	.venv/bin/python scripts/build_readme.py
