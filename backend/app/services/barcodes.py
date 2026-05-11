"""Barcode rendering service — produces PNG bytes for 1D + QR codes.

Uses `python-barcode` for the linear formats (it handles checksum
computation and rejects malformed input via BarcodeError) and `qrcode`
for QR. Returns raw PNG bytes; the route layer wraps them in a Flask
response with cache headers.
"""

from __future__ import annotations

import enum
import io

import barcode
import qrcode
from barcode.errors import BarcodeError
from barcode.writer import ImageWriter
from qrcode.constants import ERROR_CORRECT_M


class BarcodeType(enum.StrEnum):
    EAN13 = "ean13"
    EAN14 = "ean14"
    GTIN = "gtin"
    CODE128 = "code128"
    GS1_128 = "gs1_128"  # alias many people call "EAN-128"
    QR = "qr"


class BarcodeRenderError(ValueError):
    """Raised when the supplied data is invalid for the requested type."""


# Map our public names to python-barcode's identifiers
_PYTHON_BARCODE_MAP: dict[BarcodeType, str] = {
    BarcodeType.EAN13: "ean13",
    BarcodeType.EAN14: "ean14",
    BarcodeType.GTIN: "gtin",
    BarcodeType.CODE128: "code128",
    BarcodeType.GS1_128: "gs1_128",
}


def render_png(
    bc_type: BarcodeType,
    data: str,
    *,
    width_mm: float = 50,
    height_mm: float = 20,
) -> bytes:
    """Render `data` as a barcode of the given type, returning PNG bytes.

    Sized roughly to `width_mm × height_mm` at ~8 px/mm (≈200 DPI), which
    is dense enough for on-screen preview and still scans well when the
    PDF generator scales the image to the final label dimensions.
    """
    if bc_type == BarcodeType.QR:
        return _render_qr(data, height_mm=height_mm)

    try:
        cls = barcode.get_barcode_class(_PYTHON_BARCODE_MAP[bc_type])
    except KeyError as exc:
        raise BarcodeRenderError(f"unsupported type: {bc_type}") from exc

    writer = ImageWriter(format="PNG")
    # Writer options: module_height/width/text_distance in mm. text_distance
    # is the gap between the bottom of the bars and the top of the
    # human-readable digits; 5 mm clears descenders cleanly (2.5 mm let
    # the loops of "9"/"7" touch the bars).
    options = {
        "module_height": max(1.0, float(height_mm)),
        "module_width": 0.25,  # mm — bar width unit
        "dpi": 200,
        "quiet_zone": 2,
        "font_size": 8,
        "text_distance": 5.0,
        "write_text": True,
    }

    try:
        instance = cls(data, writer=writer)
    except (BarcodeError, ValueError, TypeError) as exc:
        raise BarcodeRenderError(str(exc)) from exc

    buf = io.BytesIO()
    try:
        instance.write(buf, options=options)
    except (BarcodeError, ValueError) as exc:
        raise BarcodeRenderError(str(exc)) from exc

    # Suggested width is data-dependent for 1D codes — python-barcode picks
    # its own width based on module_width and the encoded character count.
    # The frontend scales the resulting PNG to width_mm anyway.
    _ = width_mm
    return buf.getvalue()


def _render_qr(data: str, *, height_mm: float) -> bytes:
    if not data:
        raise BarcodeRenderError("QR data must not be empty")
    if len(data) > 4000:
        raise BarcodeRenderError("QR data exceeds 4000 characters")

    # box_size = pixel size per QR module; pick so the final image is
    # roughly height_mm tall at 8 px/mm.
    target_px = max(64, int(height_mm * 8))
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    if img.size[0] > target_px:
        img = img.resize((target_px, target_px))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def normalize_data(bc_type: BarcodeType, data: str) -> str:
    """Light pre-processing: strip whitespace; convert numeric types
    to digit-only strings. python-barcode does the rest."""
    data = data.strip()
    if bc_type in (BarcodeType.EAN13, BarcodeType.EAN14, BarcodeType.GTIN):
        # Drop common separators users paste from databases (e.g. 590-1234-56789-1)
        data = "".join(c for c in data if c.isdigit())
    return data
