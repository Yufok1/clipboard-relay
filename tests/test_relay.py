from __future__ import annotations

from datetime import datetime, timezone

import pytest

from clipboard_relay import ConsentRequiredError, relay
from clipboard_relay.history import HistoryEntry, append, read


def test_read_requires_explicit_consent() -> None:
    with pytest.raises(ConsentRequiredError):
        relay.read(consent="")


def test_read_returns_metadata_and_credential_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "hf_" + ("a" * 30)
    content = f"handoff payload {token}"

    monkeypatch.setattr(relay, "_detect_platform", lambda: "windows")
    monkeypatch.setattr(relay, "_read_clipboard", lambda platform: content)

    result = relay.read(consent="operator asked to read clipboard")

    assert result.content == content
    assert result.platform == "windows"
    assert result.byte_count == len(content.encode("utf-8"))
    assert result.preview == content
    assert result.has_credential_warnings
    assert result.credential_warnings[0].kind == "huggingface_token"


def test_history_round_trip_is_recent_first(tmp_path) -> None:
    history_file = tmp_path / "history.jsonl"
    older = HistoryEntry(
        timestamp=datetime(2026, 5, 22, tzinfo=timezone.utc).isoformat(),
        sha256="old",
        byte_count=3,
        preview="old",
        content="old",
    )
    newer = HistoryEntry(
        timestamp=datetime(2026, 5, 23, tzinfo=timezone.utc).isoformat(),
        sha256="new",
        byte_count=3,
        preview="new",
        content="new",
    )

    append(older, history_file=history_file)
    append(newer, history_file=history_file)

    entries = read(consent="operator asked to read history", history_file=history_file)

    assert [entry.sha256 for entry in entries] == ["new", "old"]
