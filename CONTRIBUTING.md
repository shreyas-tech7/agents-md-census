# Contributing

Thanks for helping. Start with `./init.sh`. It builds `.venv`, lints and runs every test offline.

- Write a failing test first. Say in its docstring which broken case it catches.
- Keep the run-time code on the standard library.
- Never add file text, author names or emails to anything under `data/`.
- Never type a number into the README. Run `make report`.
- To add a file format, add its path in `src/census/collect.py` and a line in `DECISIONS.md`.
- To change the drift rules, add snippets to `eval/` with labels first, then change the code.

Open an issue with the templates in `.github/ISSUE_TEMPLATE/`.
