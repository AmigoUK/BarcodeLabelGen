"""Inbound ZPL sanity validation (F29).

Every place that accepts ZPL from outside — the print queue, the import
parser, virtual-printer captures — runs this gate so obvious non-ZPL
(HTML error pages, PDFs, PostScript) is rejected with a readable reason
instead of being queued, printed or parsed into nonsense.
"""

from __future__ import annotations


class InvalidZplError(ValueError):
    """Raised when a payload fails the ZPL sanity check.

    `reason` is a short machine-friendly slug; `detail` is human-readable
    (English — the frontend maps the slug to a localized message)."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


# Magic prefixes of formats users mistake for ZPL (wrong driver, copied
# error page, wrong file). Checked case-insensitively on the lstripped head.
_KNOWN_NOT_ZPL: tuple[tuple[str, str], ...] = (
    ("<!doctype", "HTML document"),
    ("<html", "HTML document"),
    ("%pdf-", "PDF document"),
    ("%!ps", "PostScript document"),
    ("\x1b%", "PCL print stream"),
    ("\x1be", "PCL print stream"),
    ("{", "JSON document"),
)


def validate_zpl(zpl: str) -> None:
    """Raise InvalidZplError unless the payload plausibly is printable ZPL."""
    stripped = zpl.strip()
    if not stripped:
        raise InvalidZplError("empty", "payload is empty")

    head = stripped[:64].lower()
    for prefix, name in _KNOWN_NOT_ZPL:
        if head.startswith(prefix):
            raise InvalidZplError("wrong_format", f"payload looks like a {name}, not ZPL")

    start = stripped.find("^XA")
    end = stripped.rfind("^XZ")
    if start == -1:
        raise InvalidZplError("no_start", "payload contains no ^XA label start")
    if end == -1:
        raise InvalidZplError("no_end", "payload contains no ^XZ label end")
    if end < start:
        raise InvalidZplError("bad_order", "last ^XZ appears before first ^XA")
