"""Custom Pydantic types — kept loose enough for internal LAN use.

Pydantic's `EmailStr` defers to `email-validator`, which by default rejects
reserved TLDs (`.local`, `.internal`, etc.) per RFC 6761. For an internal
office tool that's almost certainly the wrong default — IT shops do use
`@company.local`-style addresses on private networks. We use a permissive
regex instead: it catches obvious typos but doesn't gate on TLD policy.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator, StringConstraints

# RFC 5321 caps the address at 254 chars (local 64 + @ + domain 255 minus 1).
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$",
)


def _validate_email(value: str) -> str:
    if not _EMAIL_RE.match(value):
        raise ValueError("not a valid email address")
    return value.lower()


LooseEmail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=254),
    AfterValidator(_validate_email),
]
