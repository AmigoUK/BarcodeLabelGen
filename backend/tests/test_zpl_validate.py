from __future__ import annotations

import pytest

from app.services.zpl import InvalidZplError, validate_zpl


def test_valid_label_passes() -> None:
    validate_zpl("^XA^FO10,10^FDok^FS^XZ")


def test_multi_label_stream_passes() -> None:
    validate_zpl("^XA^FD1^FS^XZ\n^XA^FD2^FS^XZ\n")


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ("", "empty"),
        ("   \n ", "empty"),
        ("^FO10,10^FDno envelope^FS", "no_start"),
        ("^XA^FDnever closed^FS", "no_end"),
        ("^XZ then garbage ^XA", "bad_order"),
        ("<!doctype html><h1>500</h1>", "wrong_format"),
        ("<HTML><body>err</body>", "wrong_format"),
        ("%PDF-1.7 stream", "wrong_format"),
        ("%!PS-Adobe-3.0", "wrong_format"),
        ('{"error": "json"}', "wrong_format"),
    ],
)
def test_invalid_payloads(payload: str, reason: str) -> None:
    with pytest.raises(InvalidZplError) as exc:
        validate_zpl(payload)
    assert exc.value.reason == reason
    assert exc.value.detail  # human-readable message present


def test_detail_names_the_format() -> None:
    with pytest.raises(InvalidZplError) as exc:
        validate_zpl("%PDF-1.4")
    assert "PDF" in exc.value.detail
