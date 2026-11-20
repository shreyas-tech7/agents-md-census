"""Collector: a resumable state machine over the sampled repos.

Each repo moves queued -> fetched -> cached -> done, or to failed.
States go to an append-only log next to the cache, so a stopped run resumes
where it left off. Cached answers make a repeat fetch free.
"""

from __future__ import annotations

import json
from pathlib import Path

from census.http import Fetcher, RateLimited

RAW = "https://raw.githubusercontent.com"
INSTRUCTION_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
    "GEMINI.md",
    "SKILL.md",
    ".cursorrules",
]
MANIFESTS = ["package.json", "Makefile", "pyproject.toml"]
PATHS = INSTRUCTION_FILES + MANIFESTS
STATES = ("queued", "fetched", "cached", "done", "failed")


def raw_url(repo: str, path: str, raw: str = RAW) -> str:
    return f"{raw}/{repo}/HEAD/{path}"


class StateLog:
    def __init__(self, path: Path):
        self.path = path
        self.state: dict[str, str] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self.state[rec["repo"]] = rec["state"]

    def set(self, repo: str, state: str) -> None:
        if state not in STATES:
            raise ValueError(f"unknown state {state}")
        self.state[repo] = state
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"repo": repo, "state": state}) + "\n")


class Stop(Exception):
    """Raised by the stop hook in tests to simulate a crash."""


def collect(
    fetcher: Fetcher,
    repos: list[str],
    state_path: Path,
    *,
    raw: str = RAW,
    limit: int | None = None,
    stop_at=None,
) -> dict:
    """Collect every repo not yet done. Returns counts by final state.

    stop_at(repo, state) can raise Stop to simulate a crash right after a
    state is written.
    """
    log = StateLog(state_path)
    done_now = 0
    for repo in repos:
        if log.state.get(repo) == "done":
            continue
        if limit is not None and done_now >= limit:
            break
        log.set(repo, "queued")
        _hook(stop_at, repo, "queued")
        try:
            responses = _fetch_all(fetcher, repo, raw)
        except RateLimited:
            log.set(repo, "failed")
            break
        if any(r.status not in (200, 404) for r in responses):
            log.set(repo, "failed")
            _hook(stop_at, repo, "failed")
            continue
        log.set(repo, "fetched")
        _hook(stop_at, repo, "fetched")
        for r in responses:
            if not r.from_cache:
                fetcher.store(r)
        log.set(repo, "cached")
        _hook(stop_at, repo, "cached")
        log.set(repo, "done")
        _hook(stop_at, repo, "done")
        done_now += 1
    counts = dict.fromkeys(STATES, 0)
    for repo in repos:
        counts[log.state.get(repo, "queued")] += 1
    return counts


def _fetch_all(fetcher: Fetcher, repo: str, raw: str) -> list:
    """Instruction files first. Manifests only matter for checking commands,
    so they are fetched only when the repo has an instruction file."""

    def one(path):
        url = raw_url(repo, path, raw)
        return fetcher.cached(url) or fetcher.fetch(url)

    found = [one(p) for p in INSTRUCTION_FILES]
    if any(r.status == 200 for r in found):
        found += [one(p) for p in MANIFESTS]
    return found


def _hook(stop_at, repo, state):
    if stop_at is not None:
        stop_at(repo, state)
