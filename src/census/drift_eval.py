"""Score the drift detector against hand-labeled synthetic snippets.

Three checks: the main 30 snippets, a held-out set written by a separate
agent, and the agreement between two independent label sets on the main 30.
"""

from __future__ import annotations

import json
from pathlib import Path

from census import drift
from census.stats import proportion


def score(snippets: list[dict], date: str) -> dict:
    tp = fp = fn = 0
    per = []
    for s in snippets:
        m = drift.parse_manifests(s.get("manifests", {}))
        predicted = set(drift.drift_report(s["text"], m)["drifted"])
        expected = set(s["drift"])
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        per.append({"id": s["id"], "expected": sorted(expected), "predicted": sorted(predicted)})
    return {
        "n_snippets": len(snippets),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": proportion(tp, tp + fp, date=date, label="precision", unit="predicted drift"),
        "recall": proportion(tp, tp + fn, date=date, label="recall", unit="labeled drift"),
        "per_snippet": sorted(per, key=lambda r: r["id"]),
    }


def run(snippets_path: Path, out: Path) -> dict:
    spec = json.loads(snippets_path.read_text(encoding="utf-8"))
    date = spec["labeled_on"]
    result = {"date": date, **score(spec["snippets"], date)}
    folder = snippets_path.parent
    heldout = folder / "heldout_snippets.json"
    if heldout.exists():
        h = json.loads(heldout.read_text(encoding="utf-8"))
        result["heldout"] = score(h["snippets"], h["labeled_on"])
    blind = folder / "blind_labels.json"
    if blind.exists():
        second = json.loads(blind.read_text(encoding="utf-8"))["labels"]
        same = sum(sorted(s["drift"]) == sorted(second.get(s["id"], [])) for s in spec["snippets"])
        result["label_agreement"] = proportion(
            same,
            len(spec["snippets"]),
            date=date,
            label="snippets where both labelers agree",
            unit="snippets",
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
