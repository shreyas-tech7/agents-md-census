"""Find commands in instruction files and check them against the manifests.

A command "drifts" when the file names a script or target that the root
manifest does not define. Only code is scanned: fenced blocks, inline code
spans and shell prompt lines. Prose like "use yarn instead of npm" is ignored.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

OK, DRIFT, UNVERIFIABLE = "ok", "drift", "unverifiable"

YARN_BUILTINS = {
    "add",
    "install",
    "init",
    "remove",
    "upgrade",
    "up",
    "dlx",
    "why",
    "info",
    "config",
    "cache",
    "global",
    "link",
    "unlink",
    "workspace",
    "workspaces",
    "set",
    "version",
    "publish",
    "pack",
    "login",
    "logout",
    "audit",
    "outdated",
    "create",
    "exec",
    "node",
    "plugin",
    "constraints",
    "npm",
    "bin",
    "list",
    "import",
    "licenses",
    "owner",
    "policies",
    "tag",
    "team",
    "autoclean",
    "check",
    "help",
}
PNPM_BUILTINS = {
    "add",
    "install",
    "i",
    "update",
    "up",
    "remove",
    "rm",
    "link",
    "unlink",
    "import",
    "rebuild",
    "prune",
    "fetch",
    "dlx",
    "exec",
    "create",
    "init",
    "publish",
    "pack",
    "store",
    "list",
    "ls",
    "outdated",
    "audit",
    "why",
    "env",
    "setup",
    "config",
    "server",
    "deploy",
    "patch",
    "patch-commit",
    "recursive",
    "approve-builds",
}
NAME = r"([A-Za-z0-9_][\w:.\-/@]*)"
FENCE = re.compile(r"^```.*?$(.*?)^```", re.DOTALL | re.MULTILINE)
INLINE = re.compile(r"`([^`\n]+)`")
PROMPT = re.compile(r"^\s*\$\s+(.+)$", re.MULTILINE)
WORKSPACE_FLAG = re.compile(
    r"(^|\s)(-w|--workspace|--prefix|--filter|-F|-r|--recursive|-C|--dir)(\s|=|$)"
)


@dataclass(frozen=True)
class Command:
    tool: str  # npm, pnpm, yarn, bun, make, poe
    name: str
    strict: bool  # True when a missing script cannot be a binary fallback
    scoped: bool  # True when run in a subfolder or workspace (cd, -C, --filter)

    @property
    def label(self) -> str:
        return f"{self.tool} {self.name}"


def code_segments(text: str) -> list[str]:
    """Return the code lines in a Markdown text, one string per line."""
    lines = []
    for block in FENCE.findall(text):
        lines.extend(block.splitlines())
    no_fences = FENCE.sub("", text)
    lines.extend(INLINE.findall(no_fences))
    lines.extend(PROMPT.findall(no_fences))
    return [ln.strip().lstrip("$ ").strip() for ln in lines if ln.strip()]


def _parse_segment(seg: str, scoped: bool) -> Command | None:
    words = seg.split()
    if not words:
        return None
    tool, rest = words[0], words[1:]
    scoped = scoped or bool(WORKSPACE_FLAG.search(seg))
    args = [w for w in rest if not w.startswith("-") and "=" not in w]
    if tool == "npm":
        if rest[:1] in (["run"], ["run-script"]) and len(args) >= 2:
            return Command("npm", args[1], True, scoped)
        if args[:1] in (["test"], ["t"]):
            return Command("npm", "test", True, scoped)
        return None
    if tool in ("pnpm", "yarn", "bun"):
        if args[:1] == ["run"]:
            if len(args) < 2:
                return None
            return Command(tool, args[1], tool == "pnpm", scoped)
        if tool == "bun" or not args:
            return None
        builtins = YARN_BUILTINS if tool == "yarn" else PNPM_BUILTINS
        if args[0] in builtins:
            return None
        return Command(tool, args[0], False, scoped)
    if tool in ("make", "gmake"):
        if not args:
            return None
        return Command("make", args[0], True, scoped)
    if tool == "poe" and args:
        return Command("poe", args[0], True, scoped)
    return None


def extract_commands(text: str) -> list[Command]:
    found = []
    for line in code_segments(text):
        scoped = False
        for seg in re.split(r"&&|\|\||;|\|", line):
            seg = seg.strip()
            if seg.startswith("cd "):
                scoped = True
                continue
            cmd = _parse_segment(seg, scoped)
            if cmd and re.fullmatch(NAME, cmd.name) and "<" not in cmd.name:
                found.append(cmd)
    seen, unique = set(), []
    for c in found:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


# manifests -----------------------------------------------------------------
@dataclass
class Manifests:
    npm_scripts: set | None = None  # None means no usable package.json
    make_targets: set | None = None
    make_dynamic: bool = False
    poe_tasks: set | None = None


TARGET_LINE = re.compile(r"^([^\s#:=][^:=]*?)\s*::?(?![=])", re.MULTILINE)


def parse_makefile(text: str) -> tuple[set, bool]:
    targets, dynamic = set(), False
    for m in TARGET_LINE.finditer(text):
        for t in m.group(1).split():
            if "%" in t or "$" in t:
                dynamic = True
            else:
                targets.add(t)
    if re.search(r"^\s*-?include\s", text, re.MULTILINE):
        dynamic = True
    return targets, dynamic


def parse_manifests(files: dict[str, str]) -> Manifests:
    m = Manifests()
    if "package.json" in files:
        try:
            data = json.loads(files["package.json"])
            scripts = data.get("scripts") if isinstance(data, dict) else None
            m.npm_scripts = set(scripts) if isinstance(scripts, dict) else set()
        except (json.JSONDecodeError, TypeError):
            m.npm_scripts = None
    if "Makefile" in files:
        m.make_targets, m.make_dynamic = parse_makefile(files["Makefile"])
    if "pyproject.toml" in files:
        try:
            data = tomllib.loads(files["pyproject.toml"])
            tasks = data.get("tool", {}).get("poe", {}).get("tasks")
            m.poe_tasks = set(tasks) if isinstance(tasks, dict) else None
        except (tomllib.TOMLDecodeError, TypeError, AttributeError):
            m.poe_tasks = None
    return m


def check(cmd: Command, m: Manifests) -> str:
    if cmd.scoped:
        return UNVERIFIABLE
    if cmd.tool in ("npm", "pnpm", "yarn", "bun"):
        if m.npm_scripts is None:
            return UNVERIFIABLE
        if cmd.name in m.npm_scripts:
            return OK
        return DRIFT if cmd.strict else UNVERIFIABLE
    if cmd.tool == "make":
        if m.make_targets is None:
            return UNVERIFIABLE
        if cmd.name in m.make_targets:
            return OK
        return UNVERIFIABLE if m.make_dynamic else DRIFT
    if cmd.tool == "poe":
        if m.poe_tasks is None:
            return UNVERIFIABLE
        return OK if cmd.name in m.poe_tasks else DRIFT
    return UNVERIFIABLE


def drift_report(text: str, m: Manifests) -> dict:
    results = {c.label: check(c, m) for c in extract_commands(text)}
    return {
        "n_commands": len(results),
        "n_ok": sum(v == OK for v in results.values()),
        "n_drift": sum(v == DRIFT for v in results.values()),
        "n_unverifiable": sum(v == UNVERIFIABLE for v in results.values()),
        "drifted": sorted(k for k, v in results.items() if v == DRIFT),
    }


def self_check(root: Path) -> list[tuple[str, str]]:
    """Run the detector on this repo's own instruction files."""
    files = {
        p: (root / p).read_text(encoding="utf-8")
        for p in ("package.json", "Makefile", "pyproject.toml")
        if (root / p).exists()
    }
    m = parse_manifests(files)
    bad = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = root / name
        if path.exists():
            for c in drift_report(path.read_text(encoding="utf-8"), m)["drifted"]:
                bad.append((name, c))
    return bad
