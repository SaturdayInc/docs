#!/usr/bin/env python3
"""Keep retired app claims off the published pages.

The app opens the coaching nutrition pages from its own help tips (the Setup
screens and "Make your bottles."), and Saturday AI's knowledge work reads them
too, so a page that names a control the app no longer has sends the athlete
hunting for it on the screen they are holding. Each entry below is a claim that
was true once, the reason it is not now, and the words that replaced it. Add an
entry whenever a page is corrected against the app, so the correction holds.

Run: python3 scripts/check-app-claims.py --docs .
Exit 1 lists every page and line still carrying a retired claim.
"""
import argparse
import pathlib
import re
import sys

RETIRED = [
    (r"\bUltra Eco\b|\bPurist\b",
     "the eco dial has five positions; the two split positions were switched off in the app"),
    (r"no concentration dial",
     "the athlete picks a filling method on Make your bottles.: Concentrate, Goldilocks, Evenly, or Keep 1 Fresh H2O"),
    (r"stored per activity type|slot count for that activity type|slots for the chosen activity type",
     "an athlete can keep several named Setups per sport, tagged by discipline"),
    (r"\bAI coach",
     "Saturday's AI is the assistant; coach means a human coach"),
]


def scan(root: pathlib.Path):
    """Yield (path, line number, reason) for every retired claim on a published page."""
    for path in sorted(root.rglob("*.mdx")):
        if "drafts" in path.parts or "node_modules" in path.parts:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern, reason in RETIRED:
                if re.search(pattern, line, re.IGNORECASE):
                    yield path.relative_to(root), n, reason


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", default=".")
    args = parser.parse_args()
    hits = list(scan(pathlib.Path(args.docs)))
    for path, n, reason in hits:
        print(f"{path}:{n}  {reason}")
    if hits:
        print(f"{len(hits)} retired app claim(s) on published pages.")
        return 1
    print("Clean: no retired app claims.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
