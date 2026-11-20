"""The `census` command: sample, collect, analyze, report and helpers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from census import collect as collect_mod
from census import sample as sample_mod
from census.http import Fetcher, real_token

DEFAULT_CACHE = ".cache/census"
DEFAULT_SEED = 20261120


def _fetcher(args, min_interval):
    return Fetcher(args.cache, min_interval=min_interval, token=real_token())


def cmd_sample(args):
    fetcher = _fetcher(args, args.min_interval)
    rows, meta = sample_mod.sample(fetcher, args.per_stratum, args.seed, api=args.api)
    sample_mod.write_sample(rows, meta, Path(args.data))
    print(f"sampled {len(rows)} repos from {len(meta['queries'])} strata")


def cmd_collect(args):
    fetcher = _fetcher(args, args.min_interval)
    rows = sample_mod.read_sample(Path(args.data))
    counts = collect_mod.collect(
        fetcher,
        [r["repo"] for r in rows],
        Path(args.cache) / "collect_state.jsonl",
        raw=args.raw,
        limit=args.limit,
    )
    print(json.dumps(counts, sort_keys=True), f"live_requests={fetcher.live_requests}")


def cmd_analyze(args):
    from census import dataset

    summary = dataset.build(Path(args.cache), Path(args.data), Path(args.results), raw=args.raw)
    print(f"analyzed {summary['n_repos']} repos, {summary['n_files']} instruction files")


def cmd_report(args):
    from census import report

    report.build_site(Path(args.results), Path(args.site))
    print(f"wrote {args.site}/index.html")


def cmd_drift_eval(args):
    from census import drift_eval

    result = drift_eval.run(Path(args.snippets), Path(args.out))
    print(json.dumps({k: result[k] for k in ("precision", "recall", "n_snippets")}, sort_keys=True))


def cmd_self_check(args):
    from census import drift

    bad = drift.self_check(Path(args.root))
    for path, cmd in bad:
        print(f"DRIFT {path}: {cmd}")
    print(f"self-check: {len(bad)} drifted commands")
    return 1 if bad else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="census", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--cache", default=DEFAULT_CACHE)
        sp.add_argument("--data", default="data")
        sp.add_argument("--raw", default=collect_mod.RAW)

    sp = sub.add_parser("sample", help="draw the stratified sample through GitHub Search")
    common(sp)
    sp.add_argument("--per-stratum", type=int, default=15)
    sp.add_argument("--seed", type=int, default=DEFAULT_SEED)
    sp.add_argument("--api", default=sample_mod.API)
    sp.add_argument("--min-interval", type=float, default=2.1)
    sp.set_defaults(func=cmd_sample)

    sp = sub.add_parser("collect", help="fetch instruction files and manifests, with cache")
    common(sp)
    sp.add_argument("--limit", type=int, default=None)
    sp.add_argument("--min-interval", type=float, default=0.25)
    sp.set_defaults(func=cmd_collect)

    sp = sub.add_parser("analyze", help="analyze cached files and write the dataset")
    common(sp)
    sp.add_argument("--results", default="results")
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("report", help="build the static report site")
    sp.add_argument("--results", default="results")
    sp.add_argument("--site", default="docs/report")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("drift-eval", help="score the drift detector on labeled snippets")
    sp.add_argument("--snippets", default="eval/drift_snippets.json")
    sp.add_argument("--out", default="results/drift_eval.json")
    sp.set_defaults(func=cmd_drift_eval)

    sp = sub.add_parser("self-check", help="run the drift detector on this repo's own files")
    sp.add_argument("--root", default=".")
    sp.set_defaults(func=cmd_self_check)

    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
