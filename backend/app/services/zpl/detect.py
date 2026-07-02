"""Best-effort printhead-density (DPI) detection for pasted ZPL.

ZPL doesn't carry its authoring resolution, so importing at the wrong DPI
scales every coordinate. When the label declares its size in dots via
`^PW` / `^LL`, we can recover the DPI by asking which candidate density
turns those dots into the physical label size the user is aiming for
(the current template dimensions). Without a target we fall back to the
density that yields a physically plausible label, else the 203-dpi default.
"""

from __future__ import annotations

from app.services.zpl.parser import tokenize
from app.services.zpl.units import DEFAULT_DPI, DPMM_BY_DPI

# Densities we choose between — the two common Zebra printheads.
_CANDIDATE_DPIS = (203, 300)
# A label side outside this mm range is treated as physically implausible.
_PLAUSIBLE_MM = (10.0, 300.0)


def scan_pw_ll(zpl: str) -> tuple[int | None, int | None]:
    """Return the (^PW, ^LL) dot values found in the stream, or None each."""
    pw: int | None = None
    ll: int | None = None
    for tok in tokenize(zpl):
        if tok.code == "PW":
            pw = _first_int(tok.params)
        elif tok.code == "LL":
            ll = _first_int(tok.params)
    return pw, ll


def _first_int(params: str) -> int | None:
    head = params.split(",")[0].strip()
    try:
        return int(float(head))
    except (ValueError, TypeError):
        return None


def _rel_err(value: float, target: float) -> float:
    if target <= 0:
        return float("inf")
    return abs(value - target) / target


def detect_dpi(
    zpl: str,
    *,
    target_width_mm: float | None = None,
    target_height_mm: float | None = None,
) -> int:
    """Detect the most likely authoring DPI (203 or 300).

    Priority:
      1. ^PW/^LL present + a target label size → pick the density whose
         dots→mm best matches the target.
      2. ^PW present, no target → pick the density giving a plausible
         physical width, if exactly one candidate qualifies.
      3. Otherwise → the 203-dpi default.
    """
    pw, ll = scan_pw_ll(zpl)

    if pw and target_width_mm:
        def score(dpi: int) -> float:
            dpmm = DPMM_BY_DPI[dpi]
            err = _rel_err(pw / dpmm, target_width_mm)
            if ll and target_height_mm:
                err += _rel_err(ll / dpmm, target_height_mm)
            return err

        return min(_CANDIDATE_DPIS, key=score)

    if pw:
        lo, hi = _PLAUSIBLE_MM
        plausible = [d for d in _CANDIDATE_DPIS if lo <= pw / DPMM_BY_DPI[d] <= hi]
        if len(plausible) == 1:
            return plausible[0]

    return DEFAULT_DPI
