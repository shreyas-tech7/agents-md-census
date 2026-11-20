.PHONY: test lint self-check report eval

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check src tests scripts

self-check:
	.venv/bin/census self-check

eval:
	.venv/bin/census drift-eval

report:
	.venv/bin/census analyze
	.venv/bin/census report
	.venv/bin/python scripts/build_readme.py
