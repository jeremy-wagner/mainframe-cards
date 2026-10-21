"""Tests for COBOL-parity money storage (no ROUNDED → ROUND_DOWN)."""

from decimal import Decimal

import pytest

from intcalc.money import S9_04_V99, S9_09_V99, S9_10_V99, store_money


def test_store_s9_09_v99_truncates_extra_fractional_digits():
    # CBACT04C.cbl 464-465: COMPUTE into PIC S9(09)V99 without ROUNDED.
    assert store_money(Decimal("1.239"), S9_09_V99) == Decimal("1.23")
    assert store_money(Decimal("1.999"), S9_09_V99) == Decimal("1.99")


def test_store_truncates_toward_zero_for_negatives():
    assert store_money(Decimal("-1.239"), S9_09_V99) == Decimal("-1.23")
    assert store_money(Decimal("-1.999"), S9_09_V99) == Decimal("-1.99")


def test_store_s9_04_v99_rate_picture():
    # CVTRA02Y.cpy 9: DIS-INT-RATE PIC S9(04)V99.
    assert store_money(Decimal("12.345"), S9_04_V99) == Decimal("12.34")
    assert store_money(Decimal("9999.99"), S9_04_V99) == Decimal("9999.99")


def test_store_s9_10_v99_account_balance_picture():
    # CVACT01Y.cpy 7-14: ACCT-CURR-BAL PIC S9(10)V99.
    assert store_money(Decimal("1234567890.999"), S9_10_V99) == Decimal(
        "1234567890.99"
    )


def test_store_preserves_exact_two_place_values():
    assert store_money(Decimal("100.10"), S9_09_V99) == Decimal("100.10")
    assert store_money(Decimal("0"), S9_09_V99) == Decimal("0.00")


def test_store_rejects_float():
    with pytest.raises(TypeError, match="decimal.Decimal"):
        store_money(1.23, S9_09_V99)  # type: ignore[arg-type]


def test_store_overflow_s9_04_v99():
    with pytest.raises(OverflowError):
        store_money(Decimal("10000.00"), S9_04_V99)


def test_interest_style_division_then_store():
    # Shape of CBACT04C.cbl 464-465: (bal * rate) / 1200 then store V99.
    bal = Decimal("1000.00")
    rate = Decimal("18.00")
    raw = (bal * rate) / Decimal("1200")
    assert raw == Decimal("15")
    assert store_money(raw, S9_09_V99) == Decimal("15.00")

    # Fractional remainder must truncate, not round half-up.
    bal = Decimal("100.00")
    rate = Decimal("1.00")
    raw = (bal * rate) / Decimal("1200")  # 0.08333...
    assert store_money(raw, S9_09_V99) == Decimal("0.08")
