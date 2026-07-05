"""Canvas → TSPL export engine.

Public surface:
  * `generate_tspl(canvas, *, dpmm, warnings)` — canvas → TSPL text
"""

from __future__ import annotations

from app.services.tspl.generator import generate_tspl

__all__ = ["generate_tspl"]
