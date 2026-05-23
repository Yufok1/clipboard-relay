"""CLI entry point for clipboard-relay.

Usage:

    python -m clipboard_relay daemon [--interval-ms 1000]
    python -m clipboard_relay show [--limit 20] [--full]
    python -m clipboard_relay where

Or, after install with the script entry point:

    clipboard-relay daemon
    clipboard-relay show
    clipboard-relay where
"""

from __future__ import annotations

import argparse
import sys

from clipboard_relay import daemon
from clipboard_relay.history import HISTORY_FILE, read


def _cmd_show(limit: int, full: bool) -> int:
    # The operator running this CLI is the consent surface itself; the
    # invocation IS the consent. We pass an explicit token recording that.
    entries = read(consent="cli_show_invocation", limit=limit)
    if not entries:
        print(f"(no clipboard history yet — file: {HISTORY_FILE})")
        return 0

    for entry in entries:
        marker = ""
        if entry.credential_warnings:
            kinds = ", ".join(w.kind for w in entry.credential_warnings)
            marker = f" [CRED: {kinds}]"
        print(f"--- {entry.timestamp} | {entry.byte_count}B | {entry.sha256[:12]}{marker} ---")
        print(entry.content if full else entry.preview)
        print()
    return 0


def _cmd_where() -> int:
    print(HISTORY_FILE)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clipboard-relay")
    sub = parser.add_subparsers(dest="cmd", required=True)

    daemon_p = sub.add_parser("daemon", help="run polling daemon (foreground)")
    daemon_p.add_argument("--interval-ms", type=int, default=daemon.DEFAULT_INTERVAL_MS)
    daemon_p.add_argument("--max-bytes", type=int, default=daemon.DEFAULT_MAX_BYTES)

    show_p = sub.add_parser("show", help="print recent history entries")
    show_p.add_argument("--limit", type=int, default=20)
    show_p.add_argument(
        "--full",
        action="store_true",
        help="print full content of each entry (default: preview only)",
    )

    sub.add_parser("where", help="print path to the history log")

    args = parser.parse_args(argv)

    if args.cmd == "daemon":
        daemon.run(interval_ms=args.interval_ms, max_bytes=args.max_bytes)
        return 0
    if args.cmd == "show":
        return _cmd_show(limit=args.limit, full=args.full)
    if args.cmd == "where":
        return _cmd_where()
    return 1


if __name__ == "__main__":
    sys.exit(main())
