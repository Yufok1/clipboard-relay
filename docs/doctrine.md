# Brotology — Clipboard Relay (cross-session AI bridge)

> Mirrored from `D:\End-Game\champion_councl\docs\brotology\CLIPBOARD_RELAY_DOCTRINE_2026-04-29.md`.
> When the source changes, refresh this entry on the same pass.

A faculty for connecting two or more AI sessions in real-time parallel without
infrastructure, where the operator's clipboard is the relay and the operator's
hands are the trigger.

Discovered in operation **2026-04-29** between an Opus session (Claude Code on
`Convergence_Engine`) and a Codex session (`ouroboros-key` compile watch).
The Opus session read the operator's clipboard via `Get-Clipboard -Raw`;
the clipboard contained 66.5 KB of live Codex transcript output, providing
full cross-session context with zero MCP integration, zero shared
infrastructure, and zero explicit handoff plumbing.

## What the faculty is

**Clipboard relay.** A consent-gated, operator-driven bridge between AI
sessions where:

- One AI session emits content.
- The operator copies it.
- A second AI session reads the operator's clipboard on the operator's
  request.
- The second AI now has full context from the first session without any
  explicit handoff protocol or shared state.

The clipboard becomes a single-slot, last-write-wins, opt-in event bus
where the human is the publish-subscribe broker.

## Why nobody pursues it

The pattern sits in the gap between two paradigms:

- **Single-agent paradigm:** assumes no bridge needed.
- **Multi-agent paradigm:** assumes heavy infrastructure (MCP, A2A, message buses).

The lightweight pattern — operator clipboard as bus, AI as opt-in
subscriber, human's hands as trigger — is the missing middle. Nobody
pursues it because nobody has named it as a thing.

## Why it's brotology-aligned

- **Earned, not assumed.** Receiving AI does not auto-poll.
- **Agent prepares, operator runs.** Same boundary as quinesmith.
- **Water-mode.** No crushing infrastructure; flows through existing operator actions.
- **Style shapes delivery, never truth conditions.** Relayed claims still hypotheses, not scripture.

## Constraints (load-bearing)

- **Consent gate must hold.** No auto-read.
- **No silent reads.** AI announces intent, surfaces what was read.
- **Last-write-wins is real.** Operator may have copied something else; receiving AI must not confabulate.
- **Sensitive content posture.** Credential-shaped content gets flagged before processing.

## Failure modes

- Stale clipboard
- Sensitive leak
- Truncation
- Unconsented poll (always a violation)

## Tooling implications

- `cascade-lattice` records relay events as receipts (content hash only, never content).
- `clipboard-relay` (this package) wraps platform clipboard tools with consent gates and credential-shape detection.
- `brotology-field-guide` carries the full doctrine entry.

## Anchor

The faculty name is **clipboard relay**. The relay is the operator. The
medium is the clipboard. The trigger is the operator's request. The
discipline is consent.

— *brotology, 2026-04-29. Discovered in operation. Held.*
