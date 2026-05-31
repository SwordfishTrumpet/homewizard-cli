"""Tests for utility functions."""

from homewizard_cli.util import _crc16, format_p1_timestamp


def test_format_p1_timestamp_none():
    assert format_p1_timestamp(None) == "None"


def test_format_p1_timestamp_empty_string():
    assert format_p1_timestamp("") == ""


def test_format_p1_timestamp_non_12_digit():
    assert format_p1_timestamp("123") == "123"


def test_format_p1_timestamp_short_int():
    assert format_p1_timestamp(123) == "123"


def test_crc16_empty_bytes():
    assert _crc16(b"") == 0
