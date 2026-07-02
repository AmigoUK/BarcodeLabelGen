"""Tests for the ZPL/ZPL II round-trip engine (parser + generator + batch)."""

from __future__ import annotations

from app.services.zpl import (
    detect_dpi,
    dpmm_for_dpi,
    generate_zpl,
    parse_zpl,
    render_batch_zpl,
)
from app.services.zpl.fonts import family_to_zpl_font, zpl_font_to_family
from app.services.zpl.parser import tokenize
from app.services.zpl.units import (
    dots_to_mm,
    mm_to_dots,
    rotation_to_orientation,
)

# The reference label the feature was designed around: resident Arial fonts,
# a native QR, single-brace {VARIABLES}, and a parameterised print quantity.
REFERENCE = (
    "^XA\n"
    "^FO10,50^A@N,28,28,E:ARI001.TTF^CI28^FB620,3,5,L,1^FD{NAZWA}^FS\n"
    "^FO140,150,1^A@N,26,26,E:ARI000.TTF^CI28^FH\\^FDSeria:^FS\n"
    "^FO140,180,1^A@N,26,26,E:ARI000.TTF^CI28^FH\\^FDData:^FS\n"
    "^FO150,150^A@N,26,26,E:ARI001.TTF^CI28^FH\\^FD{PARTIA}^FS\n"
    "^FO150,180^A@N,26,26,E:ARI001.TTF^CI28^FH\\^FD{DATA}^FS\n"
    "^FO400,140^BQN,2,6\n"
    "^FD{EAN}^FS\n"
    "^FO50,320^A@N,26,26,E:ARI000.TTF^CI28^FH\\\n"
    "^FD{EAN}^FS\n"
    "^PQ{NoLabel},0,1,Y\n"
    "^XZ"
)


# ------------------------------------------------------------------ units ----


def test_dpmm_for_dpi() -> None:
    assert dpmm_for_dpi(203) == 8
    assert dpmm_for_dpi(300) == 12
    assert dpmm_for_dpi(999) == 8  # unknown → default 203 dpi


def test_mm_dots_roundtrip_203() -> None:
    assert mm_to_dots(10, 8) == 80
    assert dots_to_mm(80, 8) == 10.0


def test_mm_dots_300() -> None:
    assert mm_to_dots(10, 12) == 120
    assert dots_to_mm(120, 12) == 10.0


def test_detect_dpi_matches_target_size() -> None:
    # ^PW320 dots is 40 mm at 203 dpi (8 dpmm) but 26.7 mm at 300 dpi.
    assert detect_dpi("^XA^PW320^LL800^XZ", target_width_mm=40, target_height_mm=100) == 203
    # ^PW480 dots is 40 mm at 300 dpi (12 dpmm).
    assert detect_dpi("^XA^PW480^LL1200^XZ", target_width_mm=40, target_height_mm=100) == 300


def test_detect_dpi_without_pw_defaults_203() -> None:
    assert detect_dpi("^XA^FO10,10^A@N,20,20,E:ARI000.TTF^FDhi^FS^XZ", target_width_mm=40) == 203


def test_detect_dpi_no_target_uses_plausibility() -> None:
    # 3000 dots → 375 mm @203 (implausible) vs 250 mm @300 (plausible) → 300.
    assert detect_dpi("^XA^PW3000^XZ") == 300
    # No dimensions at all → default.
    assert detect_dpi("^XA^FDx^FS^XZ") == 203


def test_rotation_orientation_mapping() -> None:
    assert rotation_to_orientation(0) == ("N", False)
    assert rotation_to_orientation(90) == ("R", False)
    assert rotation_to_orientation(180) == ("I", False)
    assert rotation_to_orientation(270) == ("B", False)
    # Not a clean multiple of 90 → snapped, flagged
    letter, snapped = rotation_to_orientation(80)
    assert letter == "R" and snapped is True


# ------------------------------------------------------------------ fonts ----


def test_font_mapping_bidirectional() -> None:
    assert family_to_zpl_font("Arial", bold=True) == "E:ARI001.TTF"
    assert family_to_zpl_font("Arial", bold=False) == "E:ARI000.TTF"
    assert zpl_font_to_family("E:ARI001.TTF") == ("Arial", "bold", "normal")
    assert zpl_font_to_family("E:ARI000.TTF") == ("Arial", "normal", "normal")
    # Unknown token → safe default (raw token is preserved elsewhere)
    assert zpl_font_to_family("E:WEIRD.TTF") == ("Arial", "normal", "normal")


# --------------------------------------------------------------- tokenize ----


def test_tokenize_handles_at_font_and_newlines() -> None:
    tokens = tokenize("^FO10,20^A@N,28,28,E:ARI001.TTF\n^FDhi^FS")
    codes = [t.code for t in tokens]
    assert codes == ["FO", "A@", "FD", "FS"]
    # Newline between A@ params and ^FD is stripped from the command params
    assert tokens[1].params == "N,28,28,E:ARI001.TTF"
    # Field data is preserved verbatim
    assert tokens[2].params == "hi"


# ---------------------------------------------------------------- parsing ----


def test_parse_reference_object_count_and_types() -> None:
    parsed = parse_zpl(REFERENCE, 8)
    objs = parsed["canvas_data"]["objects"]
    kinds = [o["type"] for o in objs]
    # 6 text fields + 1 QR
    assert kinds.count("text") == 6
    assert kinds.count("barcode") == 1


def test_parse_reference_first_text_geometry() -> None:
    obj = parse_zpl(REFERENCE, 8)["canvas_data"]["objects"][0]
    assert obj["type"] == "text"
    assert obj["x"] == 1.25 and obj["y"] == 6.25  # 10,50 dots @ 8 dpmm
    assert obj["fontSize"] == 3.5  # 28 dots
    assert obj["fontFamily"] == "Arial" and obj["fontWeight"] == "bold"
    assert obj["text"] == "{NAZWA}"
    assert obj["width"] == 77.5  # ^FB620 → 620/8 mm
    assert obj["zpl"]["font"] == "E:ARI001.TTF"


def test_parse_reference_qr() -> None:
    objs = parse_zpl(REFERENCE, 8)["canvas_data"]["objects"]
    qr = next(o for o in objs if o["type"] == "barcode")
    assert qr["barcodeType"] == "qr"
    assert qr["data"] == "{EAN}"
    assert qr["zpl"]["barcodeParams"] == "N,2,6"
    assert qr["x"] == 50.0 and qr["y"] == 17.5


def test_parse_preserves_hex_escape_and_fo_z() -> None:
    objs = parse_zpl(REFERENCE, 8)["canvas_data"]["objects"]
    seria = next(o for o in objs if o.get("text") == "Seria:")
    assert seria["zpl"]["hexEscape"] == "\\"
    assert seria["zpl"]["foZ"] == 1


def test_parse_captures_pq_variable() -> None:
    stage = parse_zpl(REFERENCE, 8)["canvas_data"]["stage"]
    assert stage["zpl"]["pq"] == "{NoLabel},0,1,Y"


def test_parse_warns_on_missing_dimensions() -> None:
    warnings = parse_zpl(REFERENCE, 8)["warnings"]
    assert any("PW" in w["message"] for w in warnings)


# --------------------------------------------------------------- generate ----


def test_generate_contains_native_commands() -> None:
    zpl = generate_zpl(parse_zpl(REFERENCE, 8)["canvas_data"])
    assert "^A@N,28,28,E:ARI001.TTF" in zpl
    assert "^BQN,2,6" in zpl
    assert "^FD{NAZWA}^FS" in zpl
    assert "^PQ{NoLabel},0,1,Y" in zpl
    assert "^FH\\" in zpl  # hex-escape char preserved


def test_roundtrip_is_a_fixed_point() -> None:
    """The first import may normalise (hoist ^CI, add ^PW/^LL), but every
    subsequent round-trip must be byte-stable."""
    g1 = generate_zpl(parse_zpl(REFERENCE, 8)["canvas_data"])
    g2 = generate_zpl(parse_zpl(g1, 8)["canvas_data"])
    assert g1 == g2


def test_generate_at_300dpi_doubles_ish_coordinates() -> None:
    canvas = parse_zpl(REFERENCE, 8)["canvas_data"]
    zpl300 = generate_zpl(canvas, dpmm=12)
    # 1.25 mm × 12 dpmm = 15 dots (vs 10 at 8 dpmm)
    assert "^FO15," in zpl300


# ------------------------------------------------------------- passthrough ---


def test_unknown_command_survives_roundtrip() -> None:
    src = "^XA\n^MMT\n^FO10,10^A@N,20,20,E:ARI000.TTF^FDhi^FS\n^XZ"
    parsed = parse_zpl(src, 8)
    # ^MMT (media mode) isn't modelled → kept as passthrough, not dropped
    zpl = generate_zpl(parsed["canvas_data"])
    assert "^MMT" in zpl
    assert "^FDhi^FS" in zpl


def test_unclassifiable_field_kept_as_raw() -> None:
    # A field with only an unmodelled command + ^FS should not vanish. The
    # command survives (insignificant whitespace inside params is normalised).
    src = "^XA\n^FO0,0^FXjust a comment^FS\n^XZ"
    zpl = generate_zpl(parse_zpl(src, 8)["canvas_data"])
    assert "^FXjust a comment" in zpl


# --------------------------------------------------------- canvas-authored ---


def test_generate_from_barcode_without_hints() -> None:
    """A barcode created in the editor (no import hints) still emits a
    native command synthesised from its type/geometry."""
    canvas = {
        "version": 1,
        "stage": {"width_mm": 50, "height_mm": 30},
        "objects": [
            {
                "id": "b1",
                "type": "barcode",
                "x": 5,
                "y": 5,
                "width": 40,
                "height": 15,
                "barcodeType": "ean13",
                "data": "590123456789",
            }
        ],
    }
    zpl = generate_zpl(canvas)
    assert "^BE" in zpl
    assert "^FD590123456789^FS" in zpl


def test_generate_text_without_hints_uses_font_map() -> None:
    canvas = {
        "version": 1,
        "stage": {"width_mm": 50, "height_mm": 30},
        "objects": [
            {
                "id": "t1",
                "type": "text",
                "x": 5,
                "y": 5,
                "text": "Hi",
                "fontSize": 4,
                "fontFamily": "Arial",
                "fontWeight": "bold",
                "fill": "#000000",
            }
        ],
    }
    zpl = generate_zpl(canvas)  # 4 mm × 8 dpmm = 32 dots
    assert "^A@N,32,32,E:ARI001.TTF" in zpl
    assert "^FDHi^FS" in zpl


# --------------------------------------------------------------- batch -------


def test_render_batch_zpl_one_block_per_row() -> None:
    canvas = {
        "version": 1,
        "stage": {"width_mm": 50, "height_mm": 30},
        "objects": [
            {
                "id": "t1",
                "type": "text",
                "x": 5,
                "y": 5,
                "text": "SKU {{sku}}",
                "fontSize": 4,
                "fontFamily": "Arial",
                "fill": "#000000",
            }
        ],
    }
    rows = [{"sku": "A001"}, {"sku": "A002"}, {"sku": "A003"}]
    out = render_batch_zpl(canvas, rows, dpmm=8).decode("utf-8")
    assert out.count("^XA") == 3 and out.count("^XZ") == 3
    assert "^FDSKU A001^FS" in out
    assert "^FDSKU A003^FS" in out


def test_render_batch_zpl_reports_progress() -> None:
    canvas = {"version": 1, "stage": {"width_mm": 20, "height_mm": 20}, "objects": []}
    calls: list[tuple[int, int]] = []
    render_batch_zpl(
        canvas,
        [{"x": "1"}, {"x": "2"}],
        dpmm=8,
        on_progress=lambda done, total: calls.append((done, total)),
    )
    assert calls == [(1, 2), (2, 2)]


def test_batch_leaves_single_brace_variables_untouched() -> None:
    """Only {{double}} placeholders substitute; {single} template variables
    are opaque and must survive for the downstream system."""
    canvas = {
        "version": 1,
        "stage": {"width_mm": 50, "height_mm": 30},
        "objects": [
            {
                "id": "t1",
                "type": "text",
                "x": 5,
                "y": 5,
                "text": "{NAZWA} {{sku}}",
                "fontSize": 4,
                "fontFamily": "Arial",
                "fill": "#000000",
            }
        ],
    }
    out = render_batch_zpl(canvas, [{"sku": "X"}], dpmm=8).decode("utf-8")
    assert "^FD{NAZWA} X^FS" in out
