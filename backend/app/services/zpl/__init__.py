"""ZPL/ZPL II round-trip engine.

Public surface:
  * `parse_zpl(zpl, dpmm)`   — ZPL text  → {"canvas_data", "warnings"}
  * `generate_zpl(canvas)`   — canvas    → ZPL text
  * `render_batch_zpl(...)`  — canvas + rows → concatenated ZPL bytes
  * `dpmm_for_dpi(dpi)`      — 203/300 dpi → 8/12 dots-per-mm
"""

from __future__ import annotations

from app.services.zpl.batch import render_batch_zpl
from app.services.zpl.detect import detect_dpi, scan_pw_ll
from app.services.zpl.generator import generate_zpl
from app.services.zpl.parser import parse_zpl
from app.services.zpl.units import DEFAULT_DPI, DEFAULT_DPMM, DPMM_BY_DPI, dpmm_for_dpi
from app.services.zpl.validate import InvalidZplError, validate_zpl

__all__ = [
    "DEFAULT_DPI",
    "DEFAULT_DPMM",
    "DPMM_BY_DPI",
    "InvalidZplError",
    "detect_dpi",
    "dpmm_for_dpi",
    "generate_zpl",
    "parse_zpl",
    "render_batch_zpl",
    "scan_pw_ll",
    "validate_zpl",
]
