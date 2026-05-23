"""Clipboard polling daemon.

Foreground process. Polls the platform clipboard at a configurable interval
and appends a :class:`HistoryEntry` for every distinct copy to the history
log.

Usage:

    python -m clipboard_relay daemon [--interval-ms 1000]

Stops on Ctrl-C. There is no fork-and-detach mode in v0.2; codex can wire
that during harden if needed.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import datetime, timezone

from clipboard_relay.history import HISTORY_FILE, HistoryEntry, append
from clipboard_relay.relay import (
    PREVIEW_CHARS,
    UnsupportedPlatformError,
    _detect_platform,
    _read_clipboard,
    _scan_for_credentials,
)

DEFAULT_INTERVAL_MS = 1000
DEFAULT_MAX_BYTES = 1_000_000


def run(
    *,
    interval_ms: int = DEFAULT_INTERVAL_MS,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> None:
    """Run the polling loop in the foreground until interrupted."""
    platform = _detect_platform()
    interval_s = interval_ms / 1000.0
    print(
        f"clipboard-relay daemon: platform={platform} log={HISTORY_FILE} "
        f"interval={interval_ms}ms max_bytes={max_bytes}",
        file=sys.stderr,
    )

    last_sha = ""

    try:
        while True:
            try:
                content = _read_clipboard(platform)
            except UnsupportedPlatformError as exc:
                # Transient failure. Back off and retry.
                print(f"clipboard-relay: read failed: {exc}", file=sys.stderr)
                time.sleep(interval_s * 2)
                continue
            except (OSError, RuntimeError) as exc:
                print(f"clipboard-relay: unexpected read error: {exc}", file=sys.stderr)
                time.sleep(interval_s * 2)
                continue

            if not content:
                time.sleep(interval_s)
                continue

            encoded = content.encode("utf-8")
            if len(encoded) > max_bytes:
                # Skip oversized clipboards. Don't crash, don't store.
                time.sleep(interval_s)
                continue

            sha256 = hashlib.sha256(encoded).hexdigest()
            if sha256 == last_sha:
                time.sleep(interval_s)
                continue

            warnings = _scan_for_credentials(content)
            entry = HistoryEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                sha256=sha256,
                byte_count=len(encoded),
                preview=content[:PREVIEW_CHARS],
                content=content,
                credential_warnings=warnings,
            )
            append(entry)
            last_sha = sha256

            preview_short = content[:60].replace("\n", " ").replace("\r", "")
            warn_marker = f" [CRED:{len(warnings)}]" if warnings else ""
            print(
                f"[{entry.timestamp}] {entry.byte_count}B {sha256[:8]}{warn_marker} "
                f"| {preview_short}",
                file=sys.stderr,
            )

            time.sleep(interval_s)
    except KeyboardInterrupt:
        print("\nclipboard-relay daemon: stopped", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="clipboard-relay-daemon",
        description="Polling daemon for clipboard-relay history",
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=DEFAULT_INTERVAL_MS,
        help=f"poll interval in milliseconds (default: {DEFAULT_INTERVAL_MS})",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"skip clipboards larger than this (default: {DEFAULT_MAX_BYTES})",
    )
    args = parser.parse_args(argv)
    run(interval_ms=args.interval_ms, max_bytes=args.max_bytes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
