from __future__ import annotations

from datetime import date

from app.services.placeholders import (
    evaluate_date_key,
    substitute_date_string,
    substitute_dates_in_canvas,
)

TODAY = date(2026, 7, 4)


# --- syntax --------------------------------------------------------------


def test_plain_date() -> None:
    assert evaluate_date_key("date", today=TODAY) == "04.07.2026"


def test_plus_days() -> None:
    assert evaluate_date_key("date+14d", today=TODAY) == "18.07.2026"


def test_minus_days() -> None:
    assert evaluate_date_key("date-7d", today=TODAY) == "27.06.2026"


def test_plus_months() -> None:
    assert evaluate_date_key("date+3m", today=TODAY) == "04.10.2026"


def test_plus_years() -> None:
    assert evaluate_date_key("date+1y", today=TODAY) == "04.07.2027"


def test_offset_with_format() -> None:
    assert evaluate_date_key("date+14d:DD/MM/YY", today=TODAY) == "18/07/26"


def test_invalid_keys_return_none() -> None:
    for key in ("date+xyz", "date+14w", "date +14d", "date+1d:", "dateX", "name"):
        assert evaluate_date_key(key, today=TODAY) is None, key


# --- arithmetic edge cases ------------------------------------------------


def test_month_end_clamps_non_leap() -> None:
    assert evaluate_date_key("date+1m", today=date(2026, 1, 31)) == "28.02.2026"


def test_month_end_clamps_leap() -> None:
    assert evaluate_date_key("date+1m", today=date(2024, 1, 31)) == "29.02.2024"


def test_leap_day_plus_year() -> None:
    assert evaluate_date_key("date+1y", today=date(2024, 2, 29)) == "28.02.2025"


def test_year_rollover() -> None:
    assert evaluate_date_key("date+2m", today=date(2026, 12, 15)) == "15.02.2027"


# --- formatting -------------------------------------------------------------


def test_format_iso() -> None:
    assert evaluate_date_key("date:YYYY-MM-DD", today=TODAY) == "2026-07-04"


def test_format_month_year_only() -> None:
    assert evaluate_date_key("date+3m:MM.YYYY", today=TODAY) == "10.2026"


def test_format_yyyy_takes_precedence_over_yy() -> None:
    # YYYY must be substituted before YY or "2026" would become "26YY"-ish
    assert evaluate_date_key("date:YYYY/YY", today=TODAY) == "2026/26"


def test_format_literal_chars_pass_through() -> None:
    assert evaluate_date_key("date:DD MM YYYY r.", today=TODAY) == "04 07 2026 r."


# --- string / canvas substitution -------------------------------------------


def test_substitute_date_string_leaves_columns_verbatim() -> None:
    out = substitute_date_string("{{name}} exp {{date+1d}}", today=TODAY)
    assert out == "{{name}} exp 05.07.2026"


def test_substitute_date_string_strips_whitespace() -> None:
    assert substitute_date_string("{{ date+1d }}", today=TODAY) == "05.07.2026"


def test_substitute_dates_in_canvas_touches_text_and_barcode_only() -> None:
    canvas = {
        "stage": {"width_mm": 50},
        "objects": [
            {"type": "text", "text": "EXP {{date+1y}}"},
            {"type": "barcode", "data": "{{date:YYYYMMDD}}"},
            {"type": "rect", "x": 0},
            {"type": "text", "text": "{{name}}"},
        ],
    }
    out = substitute_dates_in_canvas(canvas, today=TODAY)
    assert out["objects"][0]["text"] == "EXP 04.07.2027"
    assert out["objects"][1]["data"] == "20260704"
    assert out["objects"][2] == {"type": "rect", "x": 0}
    assert out["objects"][3]["text"] == "{{name}}"
    # original untouched
    assert canvas["objects"][0]["text"] == "EXP {{date+1y}}"
