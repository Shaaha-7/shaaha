"""
shaaha.cli
==========
Command-line entry point, installed as the `shaaha` console script.

    shaaha status
    shaaha diagnose [domain]
    shaaha list-backends [domain]
    shaaha dashboard [--port PORT] [--no-browser]
"""
from __future__ import annotations

import argparse
import json


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="shaaha", description="Shaaha meta-dispatcher CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show environment and adaptive-brain status as JSON")

    p_diag = sub.add_parser("diagnose", help="Show why each backend would (or wouldn't) be selected")
    p_diag.add_argument("domain", nargs="?", default=None, help="Limit to one domain, e.g. 'ml'")

    p_list = sub.add_parser("list-backends", help="List all registered backends")
    p_list.add_argument("domain", nargs="?", default=None)

    p_dash = sub.add_parser("dashboard", help="Launch the benchmark dashboard web UI")
    p_dash.add_argument("--port", type=int, default=7842)
    p_dash.add_argument("--no-browser", action="store_true", help="Don't auto-open a browser tab")

    args = parser.parse_args(argv)

    import shaaha

    if args.command == "status":
        print(json.dumps(shaaha.status(), indent=2, default=str))
    elif args.command == "diagnose":
        shaaha.diagnose(args.domain)
    elif args.command == "list-backends":
        shaaha.list_backends(args.domain)
    elif args.command == "dashboard":
        shaaha.dashboard(port=args.port, open_browser=not args.no_browser)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
