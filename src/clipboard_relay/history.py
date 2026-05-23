"""Append-only clipboard history log.

The clipboard is a single-slot, last-write-wins surface. The history log
upgrades it to a versioned timeline: every distinct copy gets a timestamped
entry, persistent across reboots, readable by both the operator and any
consenting AI session.

The log lives at ``~/.clipboard-relay/history.jsonl`` by default. Each line
is one ``HistoryEntry`` serialized as JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from clipboard_relay.relay import ConsentRequiredError, CredentialWarning

HISTORY_DIR: Path = Path.home() / ".clipboard-relay"
HISTORY_FILE: Path = HISTORY_DIR / "history.jsonl"


@dataclass(frozen=True)
class HistoryEntry:
    """A single clipboard observation captured by the daemon."""

    timestamp: str
    """ISO 8601 UTC timestamp."""

    sha256: str
    """SHA-256 of the content. Used to deduplicate; safe for receipts."""

    byte_count: int
    """UTF-8 byte length."""

    preview: str
    """First 500 characters of content. Safe for display / logging."""

    content: str
    """Full content. Treat as sensitive if ``credential_warnings`` is non-empty."""

    credential_warnings: list[CredentialWarning] = field(default_factory=list)
    """Credential-shaped matches found in content. Empty if none detected."""

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> HistoryEntry:
        raw_warnings = d.get("credential_warnings", [])
        warnings: list[CredentialWarning] = []
        if isinstance(raw_warnings, list):
            for w in raw_warnings:
                if isinstance(w, dict):
                    warnings.append(
                        CredentialWarning(
                            kind=str(w.get("kind", "")),
                            matched_text=str(w.get("matched_text", "")),
                            confidence=float(w.get("confidence", 0.0)),
                            note=str(w.get("note", "")),
                        )
                    )
        byte_count = d["byte_count"]
        if not isinstance(byte_count, (str, bytes, bytearray, int)):
            raise TypeError("byte_count must be int-like")

        return cls(
            timestamp=str(d["timestamp"]),
            sha256=str(d["sha256"]),
            byte_count=int(byte_count),
            preview=str(d["preview"]),
            content=str(d["content"]),
            credential_warnings=warnings,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
            "preview": self.preview,
            "content": self.content,
            "credential_warnings": [asdict(w) for w in self.credential_warnings],
        }


def append(entry: HistoryEntry, *, history_file: Path = HISTORY_FILE) -> None:
    """Append a single entry to the history JSONL file.

    Creates the parent directory if needed. Atomic at the line level
    because each write is one ``write()`` syscall on a small string.
    """
    history_file.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry.to_dict(), ensure_ascii=False)
    with history_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read(
    *,
    consent: str,
    limit: int = 50,
    since: datetime | None = None,
    history_file: Path = HISTORY_FILE,
) -> list[HistoryEntry]:
    """Read recent history entries, most recent first, with consent gate.

    Args:
        consent: Explicit operator consent token. Same boundary as
            :func:`clipboard_relay.relay.read`.
        limit: Max entries to return (most recent first). Default 50.
        since: Only return entries with timestamp >= ``since``.
        history_file: Path to the JSONL file.

    Returns:
        List of :class:`HistoryEntry`, ordered most-recent-first.

    Raises:
        ConsentRequiredError: If ``consent`` is empty or whitespace.
    """
    if not consent or not consent.strip():
        raise ConsentRequiredError(
            "clipboard_relay.history.read() requires an explicit, non-empty "
            "consent token. The AI must not call this without operator intent."
        )

    if not history_file.exists():
        return []

    entries: list[HistoryEntry] = []
    with history_file.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            try:
                entries.append(HistoryEntry.from_dict(payload))
            except (KeyError, ValueError, TypeError):
                continue

    # Most recent first.
    entries.reverse()

    if since is not None:
        since_iso = since.isoformat()
        entries = [e for e in entries if e.timestamp >= since_iso]

    return entries[:limit]
