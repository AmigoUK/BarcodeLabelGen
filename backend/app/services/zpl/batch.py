"""Batch ZPL rendering — one `^XA … ^XZ` block per data row.

Reuses the PDF batch renderer's `{{column}}` substitution so the two output
formats stay in lockstep: a placeholder that fills correctly in the PDF
fills identically here. Note this is orthogonal to the single-brace
`{NAZWA}` template variables, which are opaque text left for the downstream
system — the substitution only touches `{{double-brace}}` names.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from app.services.batch_render import substitute_object
from app.services.zpl.generator import generate_zpl
from app.services.zpl.units import DEFAULT_DPMM

ProgressCallback = Callable[[int, int], None]


def render_batch_zpl(
    canvas_data: dict[str, Any],
    rows: Iterable[dict[str, Any]],
    *,
    dpmm: int = DEFAULT_DPMM,
    on_progress: ProgressCallback | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> bytes:
    """Render one ZPL label per row, returning the concatenated stream as
    UTF-8 bytes. With no rows, emits the template once (variables intact)."""
    base_objects = canvas_data.get("objects") or []
    rows_list = list(rows)
    total = len(rows_list)

    blocks: list[str] = []
    if total == 0:
        blocks.append(generate_zpl(canvas_data, dpmm=dpmm, warnings=warnings))
        return ("\n".join(blocks) + "\n").encode("utf-8")

    for i, row in enumerate(rows_list):
        substituted = [substitute_object(obj, row) for obj in base_objects]
        row_canvas = {**canvas_data, "objects": substituted}
        row_warnings: list[dict[str, Any]] | None = [] if warnings is not None else None
        blocks.append(generate_zpl(row_canvas, dpmm=dpmm, warnings=row_warnings))
        if warnings is not None and row_warnings:
            for w in row_warnings:
                warnings.append({**w, "row": i + 1})
        if on_progress is not None:
            on_progress(i + 1, total)

    return ("\n".join(blocks) + "\n").encode("utf-8")
