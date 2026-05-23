# clipboard-relay

> Consent-gated, operator-driven clipboard bridge between AI sessions.

The lightweight middle between single-agent and multi-agent paradigms.

## What it does

When you run two AI sessions in parallel — say, Codex on one repo and
Claude Code on another — and you want the second to see what the first
just produced, the conventional answers are heavy: MCP integration,
agent-to-agent protocols, shared message buses, agent registries.

`clipboard-relay` is the lightweight middle: the operator's clipboard
becomes a single-slot, last-write-wins event bus, and the operator's
hands are the trigger.

```
[ Source AI session ] -- emits content -->
[ Operator hits ctrl+c ]
[ Receiving AI calls clipboard_relay.read(consent=...) ]
[ Receiving AI now has full context, no infrastructure ]
```

## Boundary

The agent must not auto-poll. The agent must not read without an explicit
operator request. The agent must surface what it read. The agent must
flag credential-shaped content before processing further.

These are not omissions; they are refusals. The package's only public
function refuses to run without a consent token.

See [docs/doctrine.md](./docs/doctrine.md) for the full brotology contract.

## Install

```bash
pip install clipboard-relay
```

With cascade-lattice receipt support:

```bash
pip install "clipboard-relay[provenance]"
```

## Two surfaces

**1. One-shot read** — `clipboard_relay.read(consent=...)`. Returns the
current clipboard once, with credential-shape detection. Single-slot,
last-write-wins.

**2. Versioned history** — `clipboard_relay.daemon` watches the clipboard
and appends every distinct copy to `~/.clipboard-relay/history.jsonl`.
The history is queryable by both the operator (CLI) and any consenting AI
session (`clipboard_relay.history.read(consent=...)`).

The history surface upgrades the clipboard from single-slot to versioned
timeline: every copy timestamped, no copy lost, no manual paste needed.

### One-shot

```python
from clipboard_relay import read

# The AI must NOT fabricate the consent token. It must trace to operator intent.
result = read(consent="user said: read what I just copied from codex")

print(result.platform)               # "windows" / "macos" / "linux"
print(result.byte_count)             # int
print(result.content_sha256)         # for receipts
print(result.preview)                # first 500 chars (safe for logging)

# Flag credentials BEFORE processing further:
if result.has_credential_warnings:
    for w in result.credential_warnings:
        print(f"WARNING: {w.kind} (confidence {w.confidence}): {w.note}")
    # Stop and confirm with operator before using `result.content`.
else:
    process(result.content)
```

### Versioned history

Start the daemon (foreground; Ctrl-C to stop):

```bash
clipboard-relay daemon                    # default 1000ms poll
clipboard-relay daemon --interval-ms 500  # tighter polling
```

Inspect history (operator-side notepad):

```bash
clipboard-relay show                # last 20 entries, preview only
clipboard-relay show --limit 100    # last 100
clipboard-relay show --full         # full content of each entry
clipboard-relay where               # print path to ~/.clipboard-relay/history.jsonl
```

Read history programmatically (AI-side, consent-gated):

```python
from clipboard_relay import history

entries = history.read(
    consent="user said: read clipboard history from the codex session",
    limit=20,
)
for e in entries:
    print(e.timestamp, e.byte_count, e.sha256[:12])
    if e.credential_warnings:
        print("  CREDENTIAL DETECTED — flag to operator before processing")
    else:
        print("  preview:", e.preview[:80])
```

Each entry on disk is one JSON line at `~/.clipboard-relay/history.jsonl`.
Format is stable; codex / cascade-lattice can ingest directly.

## Platform support

| OS | Tool used | Required |
|---|---|---|
| Windows | `powershell.exe Get-Clipboard -Raw` | bundled |
| macOS | `pbpaste` | bundled |
| Linux (X11) | `xclip -selection clipboard -o` | install `xclip` |
| Linux (Wayland) | `wl-paste --no-newline` | install `wl-clipboard` |

## Failure modes the package surfaces

- **`ConsentRequiredError`** — `read()` was called with empty / whitespace
  consent. The agent failed the consent gate.
- **`ClipboardTooLargeError`** — clipboard exceeded `max_bytes` (default 1 MB).
- **`UnsupportedPlatformError`** — no clipboard tool found on host.
- **Stale clipboard** — operator copied something else after the source
  AI's emit. Not raised; up to the caller to confirm with the operator.

## Lineage

Part of the Ouroboros ecosystem:

- [`brotology-field-guide`](https://pypi.org/project/brotology-field-guide/) —
  the operator contract this package embodies.
- [`cascade-lattice`](https://pypi.org/project/cascade-lattice/) —
  optional receipt emission for relay events (anonymized; content hash only).
- [`quinesmith`](https://pypi.org/project/quinesmith/) — sibling primitive
  with the same `agent prepares, operator runs` boundary.

## License

Apache-2.0. See [LICENSE](./LICENSE).
