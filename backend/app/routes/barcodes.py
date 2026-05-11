"""Barcode preview endpoint."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import login_required

from app.services.barcodes import BarcodeRenderError, BarcodeType, normalize_data, render_png

barcodes_bp = Blueprint("barcodes", __name__)


@barcodes_bp.get("/barcodes/preview")
@login_required
def preview() -> ResponseReturnValue:
    raw_type = (request.args.get("type") or "").lower()
    data = request.args.get("data") or ""

    try:
        bc_type = BarcodeType(raw_type)
    except ValueError:
        return (
            jsonify(
                {
                    "error": "unsupported_type",
                    "detail": f"unknown barcode type {raw_type!r}",
                    "supported": [t.value for t in BarcodeType],
                }
            ),
            400,
        )

    try:
        width_mm = float(request.args.get("width_mm", "50"))
        height_mm = float(request.args.get("height_mm", "20"))
    except ValueError:
        return jsonify({"error": "invalid_dimensions"}), 400

    width_mm = max(5.0, min(width_mm, 500.0))
    height_mm = max(5.0, min(height_mm, 500.0))

    data = normalize_data(bc_type, data)

    try:
        png = render_png(bc_type, data, width_mm=width_mm, height_mm=height_mm)
    except BarcodeRenderError as exc:
        return jsonify({"error": "invalid_barcode_data", "detail": str(exc)}), 400

    response = Response(png, mimetype="image/png")
    # Same (type, data, dimensions) always produces the same image — cache
    # aggressively so the editor can re-render previews instantly.
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response
