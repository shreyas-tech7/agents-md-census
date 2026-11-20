"""Per-file statistics: size, headings, sections and overlap between files."""

from __future__ import annotations

import re

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
SECTIONS = {
    "commands": r"command|build|setup|set up|install|run|script|develop|getting started|usage|workflow",
    "style": r"style|convention|format|lint|naming|guideline",
    "testing": r"test|qa|verif",
    "architecture": r"architect|structure|layout|overview|design|module|component|directory|folder",
    "boundaries": r"boundar|don't|do not|never|restrict|rule|guardrail|security|permission|safety|avoid",
}
SECTION_RE = {k: re.compile(v, re.IGNORECASE) for k, v in SECTIONS.items()}
FILENAMES = (
    "agents.md",
    "claude.md",
    "gemini.md",
    "copilot-instructions.md",
    "skill.md",
    ".cursorrules",
)


def is_pointer(text: str) -> bool:
    """A tiny file that only points to another instruction file (or a raw symlink)."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) > 3 or len(text) > 300:
        return False
    low = text.lower()
    return any(name in low for name in FILENAMES)


def file_stats(text: str) -> dict:
    headings = [h for _, h in HEADING.findall(text)]
    stats = {
        "bytes": len(text.encode("utf-8")),
        "lines": len(text.splitlines()),
        "words": len(text.split()),
        "headings": len(headings),
        "is_pointer": is_pointer(text),
    }
    for name, rx in SECTION_RE.items():
        stats[f"sec_{name}"] = any(rx.search(h) for h in headings)
    return stats


def _line_set(text: str) -> set[str]:
    return {
        re.sub(r"\s+", " ", ln).strip().lower() for ln in text.splitlines() if len(ln.strip()) > 3
    }


def jaccard(a: str, b: str) -> float:
    sa, sb = _line_set(a), _line_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def max_overlap(texts: list[str]) -> float | None:
    """Highest line-set Jaccard between any two non-pointer files, or None."""
    real = [t for t in texts if not is_pointer(t)]
    if len(real) < 2:
        return None
    best = 0.0
    for i in range(len(real)):
        for j in range(i + 1, len(real)):
            best = max(best, jaccard(real[i], real[j]))
    return round(best, 4)
