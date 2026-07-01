"""Bidirectional mapping between the editor's font families and the
printer-resident ZPL scalable fonts.

The reference labels use Zebra's Arial fonts stored in flash memory:
`E:ARI000.TTF` (regular) and `E:ARI001.TTF` (bold). We keep a small fixed
table so a canvas-authored label emits sensible tokens, and — crucially —
so an *imported* label round-trips: the parser stashes the exact token it
saw in the object's `zpl.font` hint, and the generator prefers that hint
over this table, making the mapping lossless for anything we imported.
"""

from __future__ import annotations

# Editor family + weight  ->  resident font token.
# Families are matched by substring (lowercased) so "Arial", "Helvetica"
# and "Inter" all resolve to the Arial faces, matching the PDF renderer's
# grouping in pdf_renderer._resolve_font.
_ARIAL_REGULAR = "E:ARI000.TTF"
_ARIAL_BOLD = "E:ARI001.TTF"

# Reverse table: token (upper-cased) -> (family, weight, style).
_TOKEN_TO_FAMILY: dict[str, tuple[str, str, str]] = {
    "E:ARI000.TTF": ("Arial", "normal", "normal"),
    "E:ARI001.TTF": ("Arial", "bold", "normal"),
}


def family_to_zpl_font(
    family: str | None, *, bold: bool = False, italic: bool = False
) -> str:
    """Return the resident ZPL font token for an editor font family.

    Falls back to the Arial faces for any unrecognised family — the same
    pragmatic default the PDF renderer uses (Arial/Helvetica/Inter are
    visually interchangeable at label sizes).
    """
    _ = italic  # resident Arial faces cover regular/bold only; italic → regular
    return _ARIAL_BOLD if bold else _ARIAL_REGULAR


def zpl_font_to_family(token: str | None) -> tuple[str, str, str]:
    """Return (family, fontWeight, fontStyle) for a ZPL font token.

    Unknown tokens (other resident faces, downloaded fonts) default to
    Arial regular; the original token is preserved separately in the
    object's `zpl.font` hint so the export stays byte-faithful regardless.
    """
    if not token:
        return ("Arial", "normal", "normal")
    return _TOKEN_TO_FAMILY.get(token.upper(), ("Arial", "normal", "normal"))
