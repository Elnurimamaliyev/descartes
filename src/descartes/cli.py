"""Command line: descartes check | open | stamp."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .check import check, link_states, schema_issues
from .mapfile import MapError, load_map
from .stamp import stamp


def _plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def cmd_check(args) -> int:
    issues = check(args.map)
    for issue in issues:
        print(issue)
    errors = sum(i.level == "error" for i in issues)
    warnings = len(issues) - errors
    print(f"descartes check: {_plural(errors, 'error')}, {_plural(warnings, 'warning')} ({args.map})")
    return 1 if errors or (args.strict and warnings) else 0


def cmd_open(args) -> int:
    try:
        data = load_map(args.map)
    except MapError as e:
        print(f"error: {args.map}: {e}", file=sys.stderr)
        return 1
    problems = schema_issues(data)
    if problems:
        print(f"error: {args.map} does not match the schema; run descartes check", file=sys.stderr)
        return 1
    open_cards = [d for d in data["decisions"] if d["status"] == "open"]
    print(f"Open decisions ({len(open_cards)}):")
    for d in open_cards:
        stage = f" [{d['stage']}]" if "stage" in d else ""
        print(f"  {d['id']}{stage}: {d['question']}")
        for o in d["options"]:
            print(f"      - {o['value']} ({o['state']})")
        if d.get("notes"):
            print(f"      notes: {d['notes'].strip().splitlines()[0]}")
    by_agent = {d["id"] for d in data["decisions"] if d.get("decided_by") == "agent" and d["status"] == "decided"}
    unreviewed = {}
    for ls in link_states(args.map, data):
        if ls.decision in by_agent and ls.state != "ok":
            unreviewed.setdefault(ls.decision, []).append(f"{ls.label} ({'not stamped' if ls.state == 'unstamped' else ls.state})")
    print(f"\nAgent decisions with code not reviewed since it changed ({len(unreviewed)}):")
    for d in data["decisions"]:
        if d["id"] in unreviewed:
            print(f"  {d['id']}: {d['question']}")
            for label in unreviewed[d["id"]]:
                print(f"      {label}")
    return 0


def cmd_stamp(args) -> int:
    try:
        stamped, problems = stamp(args.map)
    except MapError as e:
        print(f"error: {args.map}: {e}", file=sys.stderr)
        return 1
    for label in stamped:
        print(f"stamped {label}")
    for p in problems:
        print(f"error: {p}")
    if not stamped and not problems:
        print("All code links are already stamped.")
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="descartes", description="Analysis decisions as reviewable cards.")
    parser.add_argument("--version", action="version", version=f"descartes {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="validate a map and check its code links for drift")
    p.add_argument("map", type=Path)
    p.add_argument("--strict", action="store_true", help="also exit 1 on warnings")
    p.set_defaults(run=cmd_check)
    p = sub.add_parser("open", help="list decisions waiting for a person")
    p.add_argument("map", type=Path)
    p.set_defaults(run=cmd_open)
    p = sub.add_parser("stamp", help="record the current hash of every code link (after a person reviewed the cards)")
    p.add_argument("map", type=Path)
    p.set_defaults(run=cmd_stamp)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
