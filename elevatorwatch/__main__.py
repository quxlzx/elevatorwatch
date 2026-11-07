"""elevatorwatch CLI — status + watch commands. Stdlib only."""

import argparse
import json
import os
import sys

from . import sources


def _match(unit, patterns) -> bool:
    if not patterns:
        return True
    hay = f"{unit.station} {unit.station_code} {' '.join(unit.lines)}".lower()
    return any(p.lower() in hay for p in patterns)


def cmd_status(args) -> int:
    units = sources.fetch(args.source)
    outages = [u for u in units if not u.in_service and _match(u, args.station)]
    if args.json:
        print(json.dumps([u.to_dict() for u in outages], indent=2))
        return 0
    if not outages:
        print("No elevator/escalator outages match your filter. 🎉")
        return 0
    print(f"{len(outages)} out-of-service unit(s):\n")
    for u in sorted(outages, key=lambda u: (u.station, u.kind)):
        line_tag = f" [{''.join(u.lines)}]" if u.lines else ""
        print(f"  🔴 {u.label()}{line_tag}")
        if u.reason:
            print(f"     reason: {u.reason}")
        if u.return_estimate:
            print(f"     {u.return_estimate}")
    return 0


def cmd_watch(args) -> int:
    """Poll once, diff against state file, print transitions. Exit 1 if new outages."""
    units = [u for u in sources.fetch(args.source) if _match(u, args.stations)]
    current = {u.key(): u for u in units if not u.in_service}

    state = {}
    if os.path.exists(args.state):
        with open(args.state) as f:
            state = json.load(f)
    known = set(state.get("out_keys", []))
    first_run = "out_keys" not in state

    newly_out = [u for k, u in current.items() if k not in known]
    back = [k for k in known if k not in current]

    os.makedirs(os.path.dirname(os.path.abspath(args.state)), exist_ok=True)
    with open(args.state, "w") as f:
        json.dump({"out_keys": list(current.keys()),
                   "units": {k: u.to_dict() for k, u in current.items()}}, f)

    if first_run:
        print(f"[seeded] tracking {len(current)} current outage(s); no alerts on first run.")
        return 0

    for u in sorted(newly_out, key=lambda u: u.station):
        extra = f" ({u.reason})" if u.reason else ""
        ret = f" — {u.return_estimate}" if u.return_estimate else ""
        print(f"🔴 OUT: {u.label()}{extra}{ret}")
    for k in sorted(back):
        prev = state.get("units", {}).get(k, {})
        from .model import Unit
        label = Unit.from_dict(prev).label() if prev else k
        print(f"🟢 BACK: {label}")

    return 1 if newly_out else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="elevatorwatch",
                                description="Track WMATA elevator/escalator outages for the stations you care about.")
    p.add_argument("--source", choices=["auto", "scrape", "api"], default="auto",
                   help="data source (default: auto — official API if WMATA_API_KEY set, else status-page scrape)")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("status", help="list current outages")
    ps.add_argument("--station", action="append", default=[],
                    help="filter: station name substring, station code, or line letter (repeatable)")
    ps.add_argument("--json", action="store_true", help="machine-readable output")
    ps.set_defaults(fn=cmd_status)

    pw = sub.add_parser("watch", help="poll once and print outage transitions (for cron)")
    pw.add_argument("--stations", nargs="*", default=[],
                    help="stations to track (substring match); empty = all")
    pw.add_argument("--state", default=os.path.expanduser("~/.elevatorwatch/state.json"),
                    help="state file path")
    pw.set_defaults(fn=cmd_watch)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
