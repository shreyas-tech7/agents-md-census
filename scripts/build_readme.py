"""Write the README results table from results/*.json. Nobody types the numbers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from census.report import update_readme

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    changed = update_readme(ROOT / "README.md", ROOT / "results")
    print("README tables updated" if changed else "README tables already current")
