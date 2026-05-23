"""clipboard-relay — consent-gated AI clipboard bridge.

A consent-gated, operator-driven bridge between AI sessions. The receiving
AI calls ``relay.read(consent=...)``; the operator's clipboard is read once,
with credential-shape detection on the way out.

Boundary:
    The agent prepares the read; the operator's clipboard contents and the
    operator's consent token decide what is read. The receiving AI must not
    auto-poll, must not read without an explicit operator request, must not
    silently process credential-shaped content.

See ``docs/doctrine.md`` for the full brotology contract.
"""

from __future__ import annotations

__version__ = "0.2.0"

from clipboard_relay import daemon, history
from clipboard_relay.history import HISTORY_FILE, HistoryEntry
from clipboard_relay.relay import (
    ClipboardRelayResult,
    ClipboardTooLargeError,
    ConsentRequiredError,
    CredentialWarning,
    UnsupportedPlatformError,
    read,
)

__all__ = (
    "HISTORY_FILE",
    "ClipboardRelayResult",
    "ClipboardTooLargeError",
    "ConsentRequiredError",
    "CredentialWarning",
    "HistoryEntry",
    "UnsupportedPlatformError",
    "__version__",
    "daemon",
    "history",
    "read",
)
