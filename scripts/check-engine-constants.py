#!/usr/bin/env python3
"""Keep engine constants out of the published docs.

WHY THIS EXISTS. This repository is public and it serves docs.saturday.fit.
The pages describe what the prescription engine promises an athlete: that
limits apply on every calculation, that they scale with the athlete, that a
partner cannot raise them. Those promises are the point of the safety page and
they belong in public. The specific values the engine clamps to are a different
thing. They are the output of years of physiology work, they are not needed to
integrate against the API, and once printed they are permanent.

The distinction this gate enforces, stated once so it does not have to be
rediscovered:

  A number the API hands the caller is documentation. max_safe_fluid_ml_per_hr
  arrives in the safety block of every response including free teasers, so
  printing it costs nothing and omitting it only makes the field mysterious.

  A number the caller must respect is a contract. carb_upper_limit_override
  accepts a bounded range, and a partner who does not know the bound gets a 400
  with no way to discover why.

  A number the engine clamps its own output to is neither. No caller sets it,
  no response carries it, and a page that prints it has published a constant
  rather than a behaviour.

WHAT IT CHECKS. Three shape rules, not a list of forbidden values. A gate that
named the constants would publish them in this file, which is self-defeating in
a public repository, and it would catch only the values someone thought to
write down. These rules catch a shape, so they also catch the constant nobody
anticipated.

  A imperial-mass   lb, lbs, pound, pounds anywhere in a published page. The
    public API is metric throughout: athletes carry weight_kg and nothing else.
    Imperial mass appears in a partner-facing page for one reason, which is that
    a body-weight coefficient is being spelled out.

  B rate-adjacent   a number touching a nutrient rate unit: g/hr, mg/hr, mL/hr,
    g/L, mg/L, units/hr, g/hour.

  B2 impact-resolution   a band_impact value that is not a multiple of the step
    its band renders on: 10 g/hr, 100 mg/hr, 100 mL/hr. A sample prescription in
    a response example is a number the API hands the caller, which this file
    already calls documentation. band_impact is not that. It is the engine's own
    output difference between one field's two probe extremes, divided by twice
    the caller's duration and scaled by a constant, so a reader with two
    responses at different durations inverts it back to a first difference of
    the engine along an axis they chose. Printing it on the band's own step
    keeps the example honest and keeps the finer number off a public page.
    Rule B cannot see any of this: the value follows the key, and the key spells
    its unit in underscores. Found live in the onboarding example.

  C nutrient ceiling  a line naming a nutrient AND a cap word AND carrying a
    number of two or more digits. Catches a ceiling stated without a unit, which
    rule B cannot see. The nutrient word is what keeps rate-limiting.mdx out of
    it: a daily call ceiling is not a fueling ceiling.

  D body-weight scaling  a line naming body weight AND carrying a number. Rule A
    sees only the imperial phrasing of a per-kilogram or per-pound coefficient.
    Restated in metric it carries no lb, no rate unit and no cap word, so nothing
    above would notice it.

WHAT A GREEN RUN DOES NOT PROVE. That the prose is right. These rules see
shapes, so a page describing a guardrail incorrectly in words passes cleanly,
the same blind spot check-docs-drift.py records for field names. It also cannot
reach git history, where a value removed today remains readable in the revision
that carried it.

ALLOWLIST. engine-constants-allowlist.txt carries the matches that are meant to
be there, each with the reason it is meant to be there. Unlike the drift
baseline it may grow, because publishing a genuinely new response field is
legitimate. It costs a line naming the value and arguing for it in a public
file that a reviewer reads, which is the deliberation this gate exists to
force. An entry matching nothing FAILS, for the reason the drift baseline gives:
a suppression that suppresses nothing would silently absorb the next real one.

Usage:
  scripts/check-engine-constants.py [--docs <dir>] [--list]
Exit: 0 clean, 1 findings.
"""
import argparse
import os
import re
import sys

ALLOWLIST_NAME = "engine-constants-allowlist.txt"

PUBLISHED_SUFFIXES = (".mdx", ".md", ".txt")

# Not published, or published as machinery rather than prose.
SKIP_DIRS = {".git", "node_modules", ".claude", ".worktrees", "images", "scripts"}
SKIP_FILES = {ALLOWLIST_NAME, "README.md", ".mintignore"}

RATE_UNITS = r"(?:g/hr|g/hour|mg/hr|mL/hr|ml/hr|g/L|mg/L|units/hr)"

RULES = {
    "imperial-mass": re.compile(r"\b(?:lbs?|pounds?)\b", re.IGNORECASE),
    "rate-adjacent": re.compile(r"\d[\d,.]*\s?" + RATE_UNITS),
}

# A per-hour field name spells its unit in underscores and the value follows the
# key, so RATE_UNITS sees neither. Only band_impact values are checked; a sample
# prescription elsewhere in a response example is a number the API hands the
# caller, which this file already calls documentation.
BAND_IMPACT = re.compile(r"band_impact", re.IGNORECASE)
IMPACT_VALUE = re.compile(
    r"\"?(?P<key>[a-z]+_(?:g|mg|ml)_per_hr)\"?\s*[:=]\s*(?P<val>-?\d+(?:\.\d+)?)"
)
# The steps the bands themselves render on (bandRoundCarb, bandRoundSodium,
# bandRoundFluid in fuel-backend/pkg/api/precision.go).
IMPACT_GRID = {"g": 10.0, "mg": 100.0, "ml": 100.0}
# A JSON band_impact object may wrap; keep looking this many lines past the key.
IMPACT_WINDOW = 6

NUTRIENT = re.compile(r"\b(?:carb|carbs|carbohydrate|sodium|fluid|hydration)\b", re.IGNORECASE)
CAP_WORD = re.compile(
    r"\b(?:cap|caps|capped|ceiling|ceilings|absolute|maximum|upper limit|tops out|no more than)\b",
    re.IGNORECASE,
)
TWO_DIGITS = re.compile(r"\d{2,}")

# Rule A only sees the imperial phrasing of a body-weight coefficient. The same
# coefficient restated in kilograms carries no lb, no rate unit and no cap word,
# so nothing above would see it. This does.
BODY_WEIGHT = re.compile(
    r"\b(?:body weight|weight in (?:kg|kilograms|pounds|lb)|weight_lb|weightLB)\b",
    re.IGNORECASE,
)


def published_files(root):
    """Every file a reader can reach, by browsing the site or cloning the repo."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if name in SKIP_FILES or not name.endswith(PUBLISHED_SUFFIXES):
                continue
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, root), full


def scan(root):
    """Return [(rule, path, line_no, match)], sorted and deduplicated per line."""
    found = []
    for rel, full in published_files(root):
        with open(full, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        impact_left = 0
        for line_no, line in enumerate(lines, 1):
            for rule, pattern in RULES.items():
                for m in dict.fromkeys(x.group(0) for x in pattern.finditer(line)):
                    found.append((rule, rel, line_no, m.strip()))
            if NUTRIENT.search(line) and CAP_WORD.search(line):
                for m in dict.fromkeys(TWO_DIGITS.findall(line)):
                    found.append(("nutrient-ceiling", rel, line_no, m))
            if BODY_WEIGHT.search(line):
                for m in dict.fromkeys(TWO_DIGITS.findall(line)):
                    found.append(("body-weight-scaling", rel, line_no, m))
            if BAND_IMPACT.search(line):
                impact_left = IMPACT_WINDOW
            if impact_left:
                impact_left -= 1
                for m in IMPACT_VALUE.finditer(line):
                    unit = m.group("key").rsplit("_per_hr", 1)[0].rsplit("_", 1)[-1]
                    grid = IMPACT_GRID.get(unit)
                    val = float(m.group("val"))
                    if grid and abs(val - round(val / grid) * grid) > 1e-9:
                        found.append(("impact-resolution", rel, line_no, m.group(0).strip()))
    return sorted(found)


def load_allowlist(root):
    """Return {(rule, path, match): why}. Format: rule<TAB>path<TAB>match<TAB>why."""
    path = os.path.join(root, ALLOWLIST_NAME)
    entries = {}
    if not os.path.exists(path):
        return entries
    with open(path, encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4 or not parts[3].strip():
                sys.stderr.write(
                    "%s:%d malformed. Format: rule<TAB>path<TAB>match<TAB>why, "
                    "and why cannot be empty.\n" % (ALLOWLIST_NAME, line_no)
                )
                sys.exit(1)
            rule, rel, match, why = (p.strip() for p in parts[:4])
            entries[(rule, rel, match)] = why
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docs", default=".", help="docs checkout to scan")
    ap.add_argument("--list", action="store_true", help="print every allowed match too")
    args = ap.parse_args()

    root = os.path.abspath(args.docs)
    allowed = load_allowlist(root)
    found = scan(root)

    unallowed = [f for f in found if (f[0], f[1], f[3]) not in allowed]
    hit_keys = {(rule, rel, match) for rule, rel, _, match in found}
    stale = sorted(k for k in allowed if k not in hit_keys)

    if args.list:
        for rule, rel, line_no, match in found:
            state = "allowed" if (rule, rel, match) in allowed else "FOUND"
            print("%-7s %-16s %s:%d  %s" % (state, rule, rel, line_no, match))
        print()

    for rule, rel, line_no, match in unallowed:
        print("%s:%d  %s  %s" % (rel, line_no, rule, match))

    if unallowed:
        print()
        print("%d engine constant(s) found in published pages." % len(unallowed))
        print()
        print("Ask which kind of number this is:")
        print("  the API returns it in a response  -> allowlist it, and say so")
        print("  a caller must respect it to avoid a 400  -> allowlist it, and say so")
        print("  the engine clamps its own output to it  -> it does not belong here.")
        print("     Say what the limit does and what narrows it, not what it equals.")
        print()
        print("Allowlist format, in %s:" % ALLOWLIST_NAME)
        print("  rule<TAB>path<TAB>match<TAB>why")

    for key in stale:
        print("%s: allowlisted %s '%s' in %s matches nothing now. Delete the line."
              % (ALLOWLIST_NAME, key[0], key[2], key[1]))

    if not unallowed and not stale:
        print("Clean: %d allowed match(es), no engine constants." % len(found))

    return 1 if (unallowed or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
