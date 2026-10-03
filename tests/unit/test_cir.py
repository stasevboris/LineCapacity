from __future__ import annotations

import pytest

from tests.helpers import SCHEMES, act
from voltplan.exchange import cir
from voltplan.scheme.model import Scheme


@pytest.mark.parametrize("path", SCHEMES, ids=[p.stem for p in SCHEMES])
def test_sample_round_trip_is_byte_exact(path):
    raw = path.read_bytes()
    assert cir.dump_bytes(cir.load_bytes(raw)) == raw


@pytest.mark.parametrize("path", SCHEMES, ids=[p.stem for p in SCHEMES])
def test_sample_counts_match_header(path):
    rows = path.read_bytes().decode("cp1251").split("\r\n")
    scheme = cir.load_bytes(path.read_bytes())
    assert [len(scheme.lines), len(scheme.poles), len(scheme.consumers),
            len(scheme.connection_points), scheme.outgoing_count] == [int(v) for v in rows[:5]]


def test_samples_are_present():
    assert len(SCHEMES) >= 18


@pytest.mark.parametrize("value, text", [
    (0.0, "0"), (5.0, "5"), (0.84, "0,84"), (-2.0, "-2"), (1293.0, "1293"),
    (0.0271978163829378, "0,0271978163829378"), (1e-15, "1E-15"), (49.8942550184878, "49,8942550184878"),
    (2.5e20, "2,5E20"),
])
def test_number_format_follows_linecapacity(value, text):
    assert cir.format_number(value) == text


def test_parse_accepts_comma_and_point():
    assert cir.parse_number("0,84") == cir.parse_number("0.84") == 0.84


def test_integer_field_rejects_fraction():
    with pytest.raises(cir.CirFormatError):
        cir.parse_int("1,5")


def test_truncated_file_is_reported():
    text = cir.dumps(act(None, kind="new"))
    with pytest.raises(cir.CirFormatError, match="закончился"):
        cir.loads(text[: len(text) // 2])


def test_garbage_is_reported():
    with pytest.raises(cir.CirFormatError):
        cir.loads("abc\r\n1\r\n")


def test_negative_header_is_reported():
    with pytest.raises(cir.CirFormatError):
        cir.loads("-1\r\n0\r\n0\r\n0\r\n0\r\n")


def test_decoding_utf8_and_cp1251():
    scheme = act(None, kind="new")
    text = cir.dumps(scheme)
    assert cir.load_bytes(text.encode("cp1251")) == cir.load_bytes(text.encode("utf-8"))
    assert cir.load_bytes(("﻿" + text).encode("utf-8")).transformer.type_name == "ТМ-250"


def test_export_uses_crlf_and_cp1251():
    raw = cir.dump_bytes(act(None, kind="new"))
    assert raw.endswith(b"\r\n")
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert "ТМ-250".encode("cp1251") in raw


def test_empty_scheme_serializes():
    text = cir.dumps(Scheme())
    assert text.startswith("0\r\n0\r\n0\r\n0\r\n0\r\n")
    assert cir.loads(text).model_dump() == Scheme().model_dump()


def test_built_scheme_survives_round_trip():
    scheme = act(None, kind="new")
    scheme = act(scheme, kind="branch_consumer", point={"x": 163, "y": 70},
                 line={"phase_mode": 1, "phase_no": 3, "length_m": 17.5},
                 consumer={"label": "дом 7", "address": "ул. Лесная, 7"})
    again = cir.loads(cir.dumps(scheme))
    assert cir.dumps(again) == cir.dumps(scheme)
    assert again.consumers[0].address == "ул. Лесная, 7"
