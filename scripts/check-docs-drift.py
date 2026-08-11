#!/usr/bin/env python3
"""Docs drift gate: prove docs.saturday.fit still describes the live API.

WHY THIS EXISTS. The published docs are what a partner builds against before
they ever call us. When the backend renames a field, retires an endpoint or
changes an event name, nothing today notices that the docs still describe the
old behaviour, so the drift is discovered by a customer whose integration
broke. This makes the common, mechanical half of that drift structurally
impossible instead of something a reader might happen to catch.

WHAT IT CHECKS, and the oracle each check trusts:

  1. endpoints  Every `METHOD /v1/...` in the docs resolves to an operation in
     fuel-backend/api/openapi.yaml. The spec is trustworthy for routes because
     fuel-backend's own openapi-drift gate proves, on every backend PR, that the
     spec's operations and the live mux registrations are the same set.

  2. fields  Every key in a ```json example resolves to a property in the spec
     OR to a `json:"..."` struct tag in the partner-facing Go packages. The
     union matters: the spec is complete for routes but NOT for response
     bodies, so checking against the spec alone reports real, correctly
     documented fields as drift and blames the docs for spec debt.

  3. events  Every webhook event name in the docs is a member of
     webhook.AllEventTypes(). Not cosmetic: registration returns on the FIRST
     unknown name, so one stale event name in a docs example means a partner
     who copies it cannot register ANY webhook, not merely that one event.

  4. undocumented  Spec operations no page mentions. Reported, never fatal. The
     guides are guides, not a generated reference, and most of these are
     correctly absent.

WHAT IT CANNOT CHECK, stated plainly so a green run is not read as more than it
is: VALUES. If a page says a default carb target is 60 g/hr and the code says
90, both are well-formed and every check here passes. Catching that needs the
numbers pulled from the code at build time, or golden responses replayed
against a live instance. Neither exists yet. This gate is the structural half.

BASELINE. api-drift-baseline.txt carries the drift that existed when the gate
landed, so pre-existing debt never blocks an unrelated PR. It is shrink-only:
a finding not listed there fails, and a listed entry that is now clean also
fails, because a suppression that no longer suppresses anything is a lie about
the state of the docs and would silently absorb the next real regression.

Usage:
  scripts/check-docs-drift.py --backend <fuel-backend checkout> [--docs <dir>]
  scripts/check-docs-drift.py --backend ... --write-baseline   (bootstrap only)
Exit: 0 clean, 1 drift found.
"""
import argparse
import difflib
import os
import re
import sys

VERBS = ("get", "post", "put", "delete", "patch")
BASELINE_NAME = "api-drift-baseline.txt"

# Go source that can contribute a field name to a partner-visible payload.
#
# This is the whole of pkg/ and cmd/ on purpose, and the width is a deliberate
# trade. Scoping it to the obvious handler packages was tried first and was
# WRONG: the coach endpoints marshal types defined in pkg/coachread, pkg/concern
# and pkg/athletedata, so the narrow scan reported thirteen real, shipped,
# correctly documented fields as fabrications. Chasing the type graph properly
# is a Go AST job; accepting any tag in the tree is the sound approximation.
#
# What that costs: a documented field sharing a name with an unrelated internal
# struct field passes. What it preserves: a name that exists NOWHERE in the
# backend still fails, which is the rename and the deletion, the two cases this
# check is for. Weaker and correct beats stronger and wrong, because a gate that
# accuses the docs of errors they did not make gets switched off within a day.
GO_API_DIRS = ("pkg", "cmd")

# Documentation directories holding pages that are not published API reference.
SKIP_DIRS = {".git", ".worktrees", ".wt", "node_modules", "drafts", "scripts", "snippets"}


def norm(path):
    """Collapse path params so {id}, {athlete_id} and {athleteId} compare equal.

    The docs and the spec name the same parameter differently on purpose: the
    spec is camelCase, the prose is whatever reads best. Comparing them
    literally would report every parameterised path as drift."""
    return re.sub(r"\{[^}]+\}", "{}", path.rstrip("/")) or "/"


# ---------------------------------------------------------------- the oracles


def spec_operations(spec_path):
    """(VERB, normalised path) -> path as written. Line-based, so this runs with
    no third-party YAML dependency, same as fuel-backend's openapi-drift gate."""
    ops, path, in_paths = {}, None, False
    for raw in open(spec_path, errors="replace"):
        line = raw.rstrip("\n")
        if re.match(r"^[a-zA-Z_]+:", line):
            in_paths = line.startswith("paths:")
            path = None
            continue
        if not in_paths:
            continue
        m = re.match(r"^  (/\S*):\s*$", line)
        if m:
            path = m.group(1)
            continue
        m = re.match(r"^    ([a-z]+):\s*$", line)
        if m and path and m.group(1) in VERBS:
            ops[(m.group(1).upper(), norm(path))] = path
    return ops


def spec_property_names(spec_path):
    """Every key declared one level under a `properties:` block."""
    names, prop_indents = set(), []
    for raw in open(spec_path, errors="replace"):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        prop_indents = [i for i in prop_indents if i < indent]
        m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m:
            continue
        key = m.group(2)
        if key in ("properties", "additionalProperties"):
            prop_indents.append(indent)
            continue
        if prop_indents and indent == prop_indents[-1] + 2:
            names.add(key)
    return names


def go_json_tags(backend):
    """Field names the Go code marshals, from struct tags. Tests are excluded:
    a name that only ever appears in a fixture is not a shipped field."""
    tags = set()
    for rel in GO_API_DIRS:
        root_dir = os.path.join(backend, rel)
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in ("testdata", "vendor")]
            for fn in files:
                if not fn.endswith(".go") or fn.endswith("_test.go"):
                    continue
                src = open(os.path.join(root, fn), errors="replace").read()
                tags.update(re.findall(r'json:"([a-zA-Z_][a-zA-Z0-9_]*)', src))
    return tags


def go_event_types(backend):
    """The exact set AllEventTypes() returns, which is what registration
    validates against. Parsed from the constants plus the function body so a
    renamed constant cannot slip past."""
    path = os.path.join(backend, "pkg", "webhook", "types.go")
    if not os.path.isfile(path):
        return None
    src = open(path, errors="replace").read()
    consts = dict(re.findall(r'(Event[A-Za-z]+)\s*=\s*"([^"]+)"', src))
    body = re.search(r"func AllEventTypes\(\)\s*\[\]string\s*\{(.*?)\n\}", src, re.S)
    if not body:
        return None
    return {consts[n] for n in re.findall(r"\b(Event[A-Za-z]+)\b", body.group(1))
            if n in consts}


# ------------------------------------------------------------- reading a page


FENCE = re.compile(r"^\s*```(\S*)")
ENDPOINT = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/v1/[A-Za-z0-9_{}/.\-]*)")
JSON_KEY = re.compile(r'"([a-z][a-z0-9_]*)"\s*:')
BACKTICKED = re.compile(r"`([a-z][a-z0-9_]*\.[a-z][a-z0-9_.]*)`")


def read_pages(docs_dir):
    """Yield (relative path, list of (line number, text, inside-json-fence))."""
    for root, dirs, files in os.walk(docs_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in sorted(files):
            if not fn.endswith(".mdx") or fn.endswith(".draft.mdx"):
                continue
            rel = os.path.relpath(os.path.join(root, fn), docs_dir)
            lines, lang, in_fence = [], None, False
            for i, raw in enumerate(open(os.path.join(root, fn), errors="replace"), 1):
                m = FENCE.match(raw)
                if m:
                    if in_fence:
                        in_fence, lang = False, None
                    else:
                        in_fence, lang = True, m.group(1)
                    continue
                lines.append((i, raw.rstrip("\n"), in_fence and lang == "json"))
            yield rel, lines


# ------------------------------------------------------------------ baselines


def load_baseline(path):
    """kind -> {identity: reason}. Blank lines and # comments ignored."""
    out = {}
    if not os.path.isfile(path):
        return out
    for raw in open(path, errors="replace"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        kind, identity = parts[0].strip(), parts[1].strip()
        reason = parts[2].strip() if len(parts) > 2 else ""
        out.setdefault(kind, {})[identity] = reason
    return out


def near(name, known, n=3):
    """Closest known spellings, so a near-miss rename reads as old -> new
    rather than as a bare 'unknown field'.

    Best effort, and it says so: string similarity finds carb_pct -> carb_percent
    and report_focus -> ai_report_focus, but a wholesale rename such as
    confidence_score -> prescription_confidence is not similar enough for any
    cutoff that does not also suggest unrelated fields. The finding itself never
    depends on this; it is a hint on top of the file and line numbers."""
    return difflib.get_close_matches(name, sorted(known), n=n, cutoff=0.72)


# -------------------------------------------------------------------- checking


def collect(docs_dir, backend, spec_path):
    """Every finding, before the baseline is applied."""
    ops = spec_operations(spec_path)
    known_fields = spec_property_names(spec_path) | go_json_tags(backend)
    events = go_event_types(backend)
    known_paths = {p for _, p in ops}
    event_namespaces = {e.split(".", 1)[0] for e in events} if events else set()

    findings = {"endpoint": [], "field": [], "event": []}
    mentioned_ops = set()

    for rel, lines in read_pages(docs_dir):
        for lineno, text, in_json in lines:
            for m in ENDPOINT.finditer(text):
                verb, raw_path = m.group(1), m.group(2)
                key = (verb, norm(raw_path))
                mentioned_ops.add(key)
                if key in ops:
                    continue
                live = sorted(v for (v, p) in ops if p == norm(raw_path))
                if live:
                    detail = (f"the spec has {', '.join(live)} on that path, "
                              f"not {verb}")
                else:
                    guess = near(norm(raw_path), known_paths, n=2)
                    detail = ("no such path in the spec"
                              + (f"; closest: {', '.join(guess)}" if guess else ""))
                findings["endpoint"].append(
                    (f"{verb} {norm(raw_path)}", rel, lineno, m.group(0), detail))

            if in_json:
                for key in JSON_KEY.findall(text):
                    if key in known_fields:
                        continue
                    guess = near(key, known_fields)
                    detail = ("in neither the spec nor any Go json tag"
                              + (f"; closest known: {', '.join(guess)}" if guess else ""))
                    findings["field"].append((key, rel, lineno, key, detail))

            if events:
                for token in BACKTICKED.findall(text):
                    ns = token.split(".", 1)[0]
                    if ns not in event_namespaces or token in events:
                        continue
                    guess = near(token, events, n=2)
                    detail = ("not returned by webhook.AllEventTypes(), so "
                              "registration rejects it and fails the whole call"
                              + (f"; closest: {', '.join(guess)}" if guess else ""))
                    findings["event"].append((token, rel, lineno, token, detail))

    undocumented = sorted(k for k in ops if k not in mentioned_ops)
    return findings, ops, undocumented, events


LABELS = {
    "endpoint": "documented endpoint that does not exist",
    "field": "documented field that exists nowhere in the API",
    "event": "documented webhook event the server rejects",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", required=True,
                    help="path to a fuel-backend checkout")
    ap.add_argument("--docs", default=None,
                    help="path to the docs checkout (default: this repo)")
    ap.add_argument("--write-baseline", action="store_true",
                    help="rewrite the baseline from today's findings (bootstrap only)")
    ap.add_argument("--list", action="store_true",
                    help="also list spec operations no page mentions")
    args = ap.parse_args()

    docs_dir = args.docs or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend = args.backend
    spec_path = os.path.join(backend, "api", "openapi.yaml")
    baseline_path = os.path.join(docs_dir, BASELINE_NAME)

    if not os.path.isfile(spec_path):
        print(f"cannot read the spec at {spec_path}")
        print("--backend must point at a fuel-backend checkout")
        return 1

    findings, ops, undocumented, events = collect(docs_dir, backend, spec_path)
    if events is None:
        print("cannot read webhook.AllEventTypes() from the backend checkout; "
              "the event check cannot run")
        return 1

    if args.write_baseline:
        lines = [
            "# Docs drift baseline, read by scripts/check-docs-drift.py.",
            "#",
            "# SHRINK-ONLY: fix the underlying problem and delete the line. A line",
            "# that no longer matches a real finding fails the gate, and so does",
            "# adding a line, because a list that can grow is not a baseline.",
            "#",
            "# Format: kind<TAB>identity<TAB>why",
        ]
        for kind in ("endpoint", "field", "event"):
            seen = {}
            for identity, rel, lineno, _raw, _detail in findings[kind]:
                seen.setdefault(identity, []).append(f"{rel}:{lineno}")
            if seen:
                lines.append("")
                lines.append(f"# {LABELS[kind]}")
            for identity in sorted(seen):
                where = ", ".join(seen[identity][:3])
                # Deliberately not a usable reason. Every entry needs a human to
                # say whether this is real debt or a limit of the check, and an
                # unedited placeholder is meant to be obvious in review.
                lines.append(f"{kind}\t{identity}\tWHY: unexplained, seen at {where}")
        open(baseline_path, "w").write("\n".join(lines) + "\n")
        total = sum(len(v) for v in findings.values())
        print(f"wrote {baseline_path}: {total} finding(s) baselined")
        return 0

    baseline = load_baseline(baseline_path)
    failed = False

    for kind in ("endpoint", "field", "event"):
        allowed = baseline.get(kind, {})
        fresh, matched = {}, set()
        for identity, rel, lineno, raw, detail in findings[kind]:
            if identity in allowed:
                matched.add(identity)
                continue
            fresh.setdefault((identity, detail), []).append((rel, lineno, raw))
        if fresh:
            failed = True
            print(f"DRIFT: {len(fresh)} {LABELS[kind]}.")
            for (identity, detail), sites in sorted(fresh.items()):
                print(f"       {identity}")
                print(f"         docs say:  {identity}")
                print(f"         API says:  {detail}")
                for rel, lineno, raw in sites[:6]:
                    print(f"         at {rel}:{lineno}  {raw}")
                if len(sites) > 6:
                    print(f"         ... and {len(sites) - 6} more")
        stale = sorted(set(allowed) - matched)
        if stale:
            failed = True
            print(f"BASELINE: {len(stale)} {kind} entr(y/ies) no longer drift. "
                  f"Delete these lines from {BASELINE_NAME}.")
            for identity in stale:
                print(f"       {identity}   ({allowed[identity]})")

    if args.list:
        print(f"\nSpec operations no page mentions ({len(undocumented)}), "
              "reported and never fatal:")
        for verb, path in undocumented:
            print(f"       {verb:6s} {ops[(verb, path)]}")

    if not failed:
        baselined = sum(len(v) for v in baseline.values())
        print(f"docs drift: clean. {len(ops)} spec operations, "
              f"{len(events)} webhook events, {baselined} baselined, "
              f"{len(undocumented)} operations undocumented (not fatal).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
