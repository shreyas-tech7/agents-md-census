"""Check every relative link and anchor in the Markdown and HTML files.

Fails on placeholder links, missing files and missing anchors. External links
are listed as "not checked" because tests and CI stay offline.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".venv", ".git", ".cache", "node_modules", "logs", "graphify-out"}
MD_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)")
HTML_LINK = re.compile(r"(?:href|src)=[\"']([^\"']+)[\"']")
BAD = ("<owner>", "TODO", "example.com")
EXEMPT = {"docs/build/BUILD_PROMPT.md"}  # the prompt quotes these words on purpose


def anchors(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    out = set(re.findall(r"id=[\"']([^\"']+)[\"']", text))
    for h in re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
        out.add(slug)
    return out


def files():
    for p in sorted(ROOT.rglob("*")):
        if p.suffix in (".md", ".html") and not (SKIP & set(p.relative_to(ROOT).parts)):
            yield p


def main() -> int:
    errors, external = [], set()
    for path in files():
        rel = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # code blocks are not links
        links = [a or b for a, b in MD_LINK.findall(text)] + HTML_LINK.findall(text)
        for link in links:
            if rel not in EXEMPT and (link == "#" or any(b in link for b in BAD)):
                errors.append(f"{rel}: placeholder link {link}")
                continue
            if re.match(r"^[a-z]+:", link):
                if link.startswith("http"):
                    external.add(link)
                continue
            target, _, anchor = link.partition("#")
            dest = (path.parent / target).resolve() if target else path
            if not dest.exists():
                errors.append(f"{rel}: missing file {link}")
            elif anchor and dest.suffix in (".md", ".html") and anchor not in anchors(dest):
                errors.append(f"{rel}: missing anchor {link}")
    for e in errors:
        print("FAIL", e)
    for link in sorted(external):
        print("not checked", link)
    print(f"check_links: {len(errors)} problems, {len(external)} external links not checked")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
