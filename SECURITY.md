# Security

`clipboard-relay` handles clipboard content, which may include secrets. Treat
all clipboard payloads as sensitive unless the operator says otherwise.

## Supported versions

Only the latest published version receives security fixes.

## Reporting

Please report security issues privately through GitHub security advisories when
available. If advisories are unavailable, open a minimal issue that does not
include secret material or exploit payloads.

## Design boundary

- `clipboard_relay.read()` requires explicit non-empty consent.
- The package does not auto-poll through the one-shot API.
- The daemon is explicit foreground operator tooling.
- Credential-shaped content is reported before downstream processing.
- Receipts, if emitted through optional provenance tooling, should use content
  hashes and metadata, not raw clipboard content.
