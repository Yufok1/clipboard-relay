"""Consent-gated clipboard relay.

The single public entry point is ``read(consent=...)``. It reads the
operator's clipboard once, checks for credential-shaped content, and
returns a typed result. There is no auto-poll, no background read, no
silent execution.
"""

from __future__ import annotations

import hashlib
import platform as platform_module
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone

DEFAULT_MAX_BYTES = 1_000_000  # 1 MB default ceiling
PREVIEW_CHARS = 500


class ConsentRequiredError(RuntimeError):
    """Raised when ``read()`` is called without an explicit consent token."""


class ClipboardTooLargeError(RuntimeError):
    """Raised when clipboard content exceeds the configured byte ceiling."""


class UnsupportedPlatformError(RuntimeError):
    """Raised when no clipboard tool is available on the host platform."""


@dataclass(frozen=True)
class CredentialWarning:
    """A credential-shaped match found in clipboard content.

    Surfaced to the caller so the receiving AI can flag the operator
    before processing further. The ``matched_text`` field carries the
    matched substring; callers should be careful not to log it verbatim
    if processing stops.
    """

    kind: str
    """Short identifier of the credential class
    (e.g. ``aws_access_key``, ``github_token``, ``private_key_block``)."""

    matched_text: str
    """The substring that matched. Treat as sensitive."""

    confidence: float
    """0.0-1.0 heuristic confidence that this is a real credential, not a coincidence."""

    note: str = ""
    """Optional human-readable note about the match."""


@dataclass(frozen=True)
class ClipboardRelayResult:
    """Result of a single clipboard relay read."""

    content: str
    """Full clipboard content, as a string."""

    byte_count: int
    """Length in bytes (UTF-8)."""

    read_timestamp: datetime
    """UTC timestamp of the read."""

    platform: str
    """``windows`` | ``macos`` | ``linux``."""

    consent_token: str
    """The consent token the caller provided. Recorded for audit."""

    content_sha256: str
    """SHA-256 of the content. Suitable for receipts; does not leak content."""

    preview: str
    """First ``PREVIEW_CHARS`` characters of the content (for logging / display)."""

    credential_warnings: tuple[CredentialWarning, ...] = field(default_factory=tuple)
    """Credential-shaped matches found in content. Empty if none detected."""

    @property
    def has_credential_warnings(self) -> bool:
        return len(self.credential_warnings) > 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read(
    consent: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> ClipboardRelayResult:
    """Read the operator's clipboard, once, with consent gate.

    Args:
        consent: Non-empty operator consent token. The recommended value
            is the operator's verbal request that prompted the read,
            e.g. ``"user asked: read clipboard"``. The AI must not
            fabricate this string; it must trace to operator intent.
            Empty / whitespace-only consent raises ``ConsentRequiredError``.
        max_bytes: Refuse to read clipboards larger than this many bytes.
            Defaults to 1 MB. Prevents accidental ingestion of huge
            content.

    Returns:
        :class:`ClipboardRelayResult` with content, metadata, and any
        credential warnings.

    Raises:
        ConsentRequiredError: if ``consent`` is empty or whitespace-only.
        ClipboardTooLargeError: if clipboard byte size exceeds ``max_bytes``.
        UnsupportedPlatformError: if no clipboard tool is found.
    """
    if not consent or not consent.strip():
        raise ConsentRequiredError(
            "clipboard_relay.read() requires an explicit, non-empty consent "
            "token. The AI must not call this function without operator intent."
        )

    platform = _detect_platform()
    content = _read_clipboard(platform)
    encoded = content.encode("utf-8")

    if len(encoded) > max_bytes:
        raise ClipboardTooLargeError(
            f"clipboard size {len(encoded)} bytes exceeds max_bytes={max_bytes}. "
            f"Increase max_bytes explicitly if this is intended."
        )

    warnings = tuple(_scan_for_credentials(content))
    sha256 = hashlib.sha256(encoded).hexdigest()
    preview = content[:PREVIEW_CHARS]

    return ClipboardRelayResult(
        content=content,
        byte_count=len(encoded),
        read_timestamp=datetime.now(timezone.utc),
        platform=platform,
        consent_token=consent,
        content_sha256=sha256,
        preview=preview,
        credential_warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Platform detection and clipboard read
# ---------------------------------------------------------------------------


def _detect_platform() -> str:
    system = platform_module.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    raise UnsupportedPlatformError(f"unsupported platform: {system}")


def _read_clipboard(platform: str) -> str:
    if platform == "windows":
        return _read_windows()
    if platform == "macos":
        return _read_macos()
    if platform == "linux":
        return _read_linux()
    raise UnsupportedPlatformError(f"unsupported platform: {platform}")


def _read_windows() -> str:
    # Use PowerShell's Get-Clipboard -Raw to preserve linebreaks.
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        raise UnsupportedPlatformError(
            f"powershell Get-Clipboard failed: {result.stderr.strip()}"
        )
    # PowerShell Get-Clipboard -Raw appends a trailing newline; preserve content as-is
    # but strip exactly one trailing newline if present, since most callers don't expect it.
    text = result.stdout
    if text.endswith("\r\n"):
        text = text[:-2]
    elif text.endswith("\n"):
        text = text[:-1]
    return text


def _read_macos() -> str:
    result = subprocess.run(
        ["pbpaste"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        raise UnsupportedPlatformError(
            f"pbpaste failed: {result.stderr.strip()}"
        )
    return result.stdout


def _read_linux() -> str:
    # Try xclip (X11) first, then wl-paste (Wayland).
    for cmd in (
        ["xclip", "-selection", "clipboard", "-o"],
        ["wl-paste", "--no-newline"],
    ):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            return result.stdout
    raise UnsupportedPlatformError(
        "no Linux clipboard tool found; install xclip (X11) or wl-clipboard (Wayland)"
    )


# ---------------------------------------------------------------------------
# Credential-shape detection
# ---------------------------------------------------------------------------

# Conservative regexes. False positives are tolerable; false negatives are the
# load-bearing concern. If a string LOOKS like a credential, we warn — the
# operator decides whether it actually is one.

_CREDENTIAL_PATTERNS: tuple[tuple[str, str, float, str], ...] = (
    (
        "aws_access_key",
        r"\bAKIA[0-9A-Z]{16}\b",
        0.95,
        "AWS access key id pattern",
    ),
    (
        "github_token",
        r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
        0.95,
        "GitHub personal / OAuth / user / server token",
    ),
    (
        "huggingface_token",
        r"\bhf_[A-Za-z0-9]{30,}\b",
        0.9,
        "Hugging Face token",
    ),
    (
        "openai_api_key",
        r"\bsk-[A-Za-z0-9_-]{20,}\b",
        0.85,
        "OpenAI / Anthropic / generic sk- prefixed API key",
    ),
    (
        "slack_token",
        r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",
        0.95,
        "Slack token",
    ),
    (
        "private_key_block",
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |)PRIVATE KEY-----",
        0.99,
        "PEM private key block",
    ),
    (
        "jwt",
        r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        0.85,
        "JSON Web Token",
    ),
    (
        "generic_bearer_header",
        r"(?i)\bauthorization:\s*bearer\s+[A-Za-z0-9._-]{16,}",
        0.9,
        "HTTP Authorization: Bearer header",
    ),
    (
        "google_api_key",
        r"\bAIza[0-9A-Za-z_-]{35}\b",
        0.95,
        "Google API key",
    ),
)


def _scan_for_credentials(content: str) -> list[CredentialWarning]:
    warnings: list[CredentialWarning] = []
    for kind, pattern, confidence, note in _CREDENTIAL_PATTERNS:
        for match in re.finditer(pattern, content):
            warnings.append(
                CredentialWarning(
                    kind=kind,
                    matched_text=match.group(0),
                    confidence=confidence,
                    note=note,
                )
            )
    return warnings
