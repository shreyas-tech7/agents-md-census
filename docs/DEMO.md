# Demo

A real terminal session from the build, on 2026-11-20. Nothing here needs a sign-in. The results page at [docs/report/index.html](report/index.html) opens from disk.

## Setup and tests, all offline

```text
$ ./init.sh
........................................                                 [100%]
40 passed in 11.44s
self-check: 0 drifted commands
init.sh: all checks passed
```

## Score the drift detector on the 30 labeled snippets

```text
$ .venv/bin/census drift-eval
{"n_snippets": 30, "precision": {"ci_high": 100.0, "ci_low": 74.1, "date": "2026-11-20", "k": 11, "label": "precision", "method": "Wilson score 95%", "n": 11, "pct": 100.0, "unit": "predicted drift"}, "recall": {"ci_high": 98.5, "ci_low": 64.6, "date": "2026-11-20", "k": 11, "label": "recall", "method": "Wilson score 95%", "n": 12, "pct": 91.7, "unit": "labeled drift"}}
```

## The repo checks its own agent files

```text
$ .venv/bin/census self-check
self-check: 0 drifted commands
```

## The last two collection chunks

Each run resumes from the state log. The second run finished the last 164 repos with none failed.

```text
$ .venv/bin/census collect --limit 200
{"cached": 0, "done": 901, "failed": 0, "fetched": 0, "queued": 164} live_requests=1245
$ .venv/bin/census collect --limit 200
{"cached": 0, "done": 1065, "failed": 0, "fetched": 0, "queued": 0} live_requests=1014
```

## Build the dataset from the cache and prove the rebuild is stable

```text
$ .venv/bin/census analyze
analyzed 1065 repos, 129 instruction files

$ scripts/rebuild_check.sh
rebuild from cache: byte for byte identical

$ python3 -c "import json; s=json.load(open('results/summary.json')); print(s['n_repos'], s['n_files'], s['cost'])"
1065 129 {'dollars': 0, 'model_calls': 0, 'raw_requests': 7350, 'raw_requests_per_repo': 6.9, 'search_requests': 144}
```
