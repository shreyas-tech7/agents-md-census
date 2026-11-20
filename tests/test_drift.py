import json
from pathlib import Path

from census import drift, drift_eval

ROOT = Path(__file__).resolve().parents[1]


def labels(text, manifests):
    return drift.drift_report(text, drift.parse_manifests(manifests))["drifted"]


def test_missing_npm_script_drifts():
    """Broken case: a detector that never reports drift."""
    pkg = {"package.json": '{"scripts": {"build": "tsc"}}'}
    assert labels("```\nnpm run build\nnpm run typecheck\n```", pkg) == ["npm typecheck"]


def test_prose_is_not_scanned():
    """Broken case: "use yarn instead of npm" read as the command `yarn instead`."""
    assert drift.extract_commands("Use yarn instead of npm for everything.") == []


def test_cd_prefix_makes_command_unverifiable():
    pkg = {"package.json": '{"scripts": {}}'}
    assert labels("```\ncd web && npm run dev\n```", pkg) == []


def test_missing_manifest_is_unverifiable_not_drift():
    rep = drift.drift_report("Run `make test`.", drift.parse_manifests({}))
    assert rep["n_unverifiable"] == 1 and rep["n_drift"] == 0


def test_makefile_targets_and_include():
    targets, dynamic = drift.parse_makefile(".PHONY: a b\na b: c\n\techo\nVAR := 1\n")
    assert {"a", "b"} <= targets and "VAR" not in targets and not dynamic
    assert drift.parse_makefile("include x.mk\n")[1]


def test_make_variable_assignment_is_skipped():
    mk = {"Makefile": "test:\n\tgo test\n"}
    assert labels("```\nmake test V=1\n```", mk) == []


def test_yarn_bin_fallback_is_unverifiable():
    pkg = {"package.json": '{"scripts": {"test": "jest"}}'}
    assert labels("`yarn eslint .`", pkg) == []


def test_poe_tasks():
    py = {"pyproject.toml": '[tool.poe.tasks]\ntest = "pytest"\n'}
    assert labels("```\npoe test\npoe format\n```", py) == ["poe format"]


def test_eval_matches_results_file(tmp_path):
    """The numbers in results/drift_eval.json must come from the current code."""
    out = tmp_path / "e.json"
    res = drift_eval.run(ROOT / "eval/drift_snippets.json", out)
    assert res["n_snippets"] == 30
    shipped = json.loads((ROOT / "results/drift_eval.json").read_text())
    assert shipped == json.loads(out.read_text())


def test_this_repo_has_no_drift():
    """Practice what the census measures: our own AGENTS.md and CLAUDE.md."""
    assert drift.self_check(ROOT) == []


def test_same_name_scoped_and_unscoped_counts_once_as_checkable():
    """Broken case: the scoped copy overwrote the root verdict, hiding drift."""
    pkg = {"package.json": '{"scripts": {"dev": "vite"}}'}
    text = "```\nnpm run build\ncd web && npm run build\n```"
    rep = drift.drift_report(text, drift.parse_manifests(pkg))
    assert rep["drifted"] == ["npm build"] and rep["n_commands"] == 1
