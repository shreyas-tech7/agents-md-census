#!/usr/bin/env bash
# Rebuild the dataset from the cache twice and compare the bytes.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .cache/census/collect_state.jsonl ]; then
  echo "no cache here: run the collection first (the unit test covers the fixture cache)"
  exit 0
fi
.venv/bin/census analyze >/dev/null
first=$(sha256sum data/census_* results/summary.json)
.venv/bin/census analyze >/dev/null
second=$(sha256sum data/census_* results/summary.json)
if [ "$first" != "$second" ]; then
  echo "rebuild differs"; exit 1
fi
echo "$first"
echo "rebuild from cache: byte for byte identical"
