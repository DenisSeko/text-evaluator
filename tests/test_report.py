"""Report tests: date/time localization for HR and US formats."""

from __future__ import annotations

from lexi_evaluator.report import format_date, format_datetime


def test_format_date_croatian() -> None:
    assert format_date("2026-01-28", "hr") == "28. siječnja 2026."


def test_format_date_american() -> None:
    assert format_date("2026-01-28", "en") == "January 28, 2026"


def test_format_datetime_croatian() -> None:
    assert format_datetime("2026-08-10T21:02:16+00:00", "hr") == "10. kolovoza 2026. u 21:02 (UTC)"


def test_format_datetime_american() -> None:
    assert format_datetime("2026-08-10T21:02:16+00:00", "en") == "August 10, 2026, 21:02 (UTC)"


def test_format_date_unknown_value_passthrough() -> None:
    assert format_date("n/a", "hr") == "n/a"
    assert format_datetime("unknown", "en") == "unknown"
