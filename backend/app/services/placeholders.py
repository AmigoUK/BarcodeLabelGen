"""Dynamic date placeholders: {{date}}, {{date+14d}}, {{date-7d:DD/MM/YY}}.

Evaluated at generation time (PDF and ZPL alike). Offset units are d/m/y;
month and year arithmetic clamps to the end of the month (Jan 31 + 1m →
Feb 28/29). Format tokens: DD MM YY YYYY (YYYY replaced before YY); any
other character passes through literally. Keys that don't match the strict
syntax return None so callers fall through to normal column handling.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from dateutil.relativedelta import relativedelta

DATE_KEY_RE = re.compile(r"^date(?:([+-])(\d+)([dmy]))?(?::(.+))?$")

DEFAULT_FORMAT = "DD.MM.YYYY"

# The shared {{...}} pattern lives in batch_render; duplicated here to keep
# this module import-light (batch_render pulls in reportlab).
PLACEHOLDER_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def _format_date(d: date, fmt: str) -> str:
    out = fmt.replace("YYYY", f"{d.year:04d}")
    out = out.replace("YY", f"{d.year % 100:02d}")
    out = out.replace("DD", f"{d.day:02d}")
    return out.replace("MM", f"{d.month:02d}")


def evaluate_date_key(key: str, *, today: date | None = None) -> str | None:
    """Return the formatted date for a date-placeholder key, or None if the
    key isn't valid date syntax (the fall-through signal for callers)."""
    m = DATE_KEY_RE.match(key)
    if m is None:
        return None
    sign, amount, unit, fmt = m.groups()
    base = today if today is not None else datetime.now().date()
    if sign is not None:
        n = int(amount) * (-1 if sign == "-" else 1)
        if unit == "d":
            base = base + relativedelta(days=n)
        elif unit == "m":
            base = base + relativedelta(months=n)
        else:
            base = base + relativedelta(years=n)
    return _format_date(base, fmt or DEFAULT_FORMAT)


def is_plain_date_key(key: str) -> bool:
    return key == "date"


def substitute_date_string(value: str, *, today: date | None = None) -> str:
    """Replace only valid date placeholders; leave every other {{...}}
    token verbatim (single-label / template paths must not blank columns)."""

    def repl(m: re.Match[str]) -> str:
        computed = evaluate_date_key(m.group(1).strip(), today=today)
        return m.group(0) if computed is None else computed

    return PLACEHOLDER_RE.sub(repl, value)


def substitute_dates_in_canvas(
    canvas_data: dict[str, Any], *, today: date | None = None
) -> dict[str, Any]:
    """Copy of the canvas with date placeholders resolved in the fields the
    renderers read — text on text objects, data on barcodes (mirrors
    batch_render.substitute_object's field selection)."""
    out = dict(canvas_data)
    objects = out.get("objects")
    if not isinstance(objects, list):
        return out
    new_objects = []
    for obj in objects:
        if isinstance(obj, dict):
            obj = dict(obj)
            kind = obj.get("type")
            if kind == "text" and isinstance(obj.get("text"), str):
                obj["text"] = substitute_date_string(obj["text"], today=today)
            elif kind == "barcode" and isinstance(obj.get("data"), str):
                obj["data"] = substitute_date_string(obj["data"], today=today)
            elif kind == "table" and isinstance(obj.get("cells"), list):
                obj["cells"] = [
                    [
                        substitute_date_string(cell, today=today) if isinstance(cell, str) else cell
                        for cell in r
                    ]
                    for r in obj["cells"]
                    if isinstance(r, list)
                ]
        new_objects.append(obj)
    out["objects"] = new_objects
    return out
