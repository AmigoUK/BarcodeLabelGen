"""Unit + geometry helpers for the ZPL round-trip.

The editor authors everything in millimetres; ZPL speaks in *dots*, whose
size depends on printhead density (dots-per-mm). 203 dpi ≈ 8 dpmm and
300 dpi ≈ 12 dpmm are the two common Zebra densities. All conversions go
through `dpmm` so a single label can be re-emitted at a different density
without touching the canvas model.
"""

from __future__ import annotations

# Supported printhead densities, keyed by the DPI value the UI exposes.
DPMM_BY_DPI: dict[int, int] = {
    152: 6,
    203: 8,
    300: 12,  # 11.8 rounded to 12 — Zebra documents 300 dpi as 12 dpmm
    600: 24,
}

DEFAULT_DPI = 203
DEFAULT_DPMM = DPMM_BY_DPI[DEFAULT_DPI]

# ZPL field orientation letter ⇄ Konva clockwise rotation in degrees.
_ORIENTATION_TO_DEG: dict[str, int] = {"N": 0, "R": 90, "I": 180, "B": 270}
_DEG_TO_ORIENTATION: dict[int, str] = {v: k for k, v in _ORIENTATION_TO_DEG.items()}


def dpmm_for_dpi(dpi: int) -> int:
    """Return dots-per-mm for a DPI value, defaulting to 203 dpi (8 dpmm)."""
    return DPMM_BY_DPI.get(int(dpi), DEFAULT_DPMM)


def mm_to_dots(mm_val: float, dpmm: int) -> int:
    """Convert millimetres to whole dots (ZPL coordinates are integers)."""
    return round(float(mm_val) * dpmm)


def dots_to_mm(dots: float, dpmm: int) -> float:
    """Convert dots to millimetres. Kept as float — the canvas stores mm."""
    if dpmm <= 0:
        dpmm = DEFAULT_DPMM
    return float(dots) / dpmm


def orientation_to_rotation(letter: str | None) -> int:
    """Map a ZPL orientation letter (N/R/I/B) to clockwise degrees."""
    return _ORIENTATION_TO_DEG.get((letter or "N").upper(), 0)


def rotation_to_orientation(rotation: float | None) -> tuple[str, bool]:
    """Map clockwise degrees to the nearest ZPL orientation letter.

    Returns (letter, snapped) where `snapped` is True when the input was not
    already a clean multiple of 90° — callers surface a warning in that case
    because ZPL fields only support four orientations.
    """
    deg = round((float(rotation or 0)) % 360)
    if deg in _DEG_TO_ORIENTATION:
        return _DEG_TO_ORIENTATION[deg], False
    nearest = min(_DEG_TO_ORIENTATION, key=lambda a: min(abs(a - deg), 360 - abs(a - deg)))
    return _DEG_TO_ORIENTATION[nearest], True
