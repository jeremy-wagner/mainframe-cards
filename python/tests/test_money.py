"""Tests for COBOL-style money picture storage (KAN-41)."""

from decimal import Decimal

import pytest

from intcalc.money import S9_04_V99, S9_09_V99, S9_10_V99, store_money


def test_truncate_fractional_digits_without_rounded():
    # COMPUTE without ROUNDED into PIC S9(09)V99 — CBACT04C.cbl:464-465, :168
    # Project money rule: non-ROUNDED → Decimal ROUND_DOWN (toward zero).
    assert store_money(Decimal("1.999"), S9_09_V99) == Decimal("1.99")
    assert store_money(Decimal("-1.999"), S9_09_V99) == Decimal("-1.99")


def test_interest_style_division_truncates_to_cents():
    # (TRAN-CAT-BAL * DIS-INT-RATE) / 1200 — CBACT04C.cbl:464-465
    # CVTRA01Y.cpy:9 balance; CVTRA02Y.cpy:9 rate
    balance = Decimal("1000.00")
    rate = Decimal("15.99")
    raw = (balance * rate) / Decimal("1200")
    assert store_money(raw, S9_09_V99) == Decimal("13.32")


def test_rate_picture_s9_04_v99():
    # DIS-INT-RATE — CVTRA02Y.cpy:9
    assert store_money(Decimal("15.999"), S9_04_V99) == Decimal("15.99")
    assert store_money(Decimal("9999.99"), S9_04_V99) == Decimal("9999.99")


def test_account_picture_s9_10_v99():
    # ACCT-CURR-BAL etc. — CVACT01Y.cpy:7-9, 13-14
    assert store_money(Decimal("1234567890.999"), S9_10_V99) == Decimal(
        "1234567890.99"
    )


def test_transaction_amount_uses_s9_09_v99():
    # TRAN-AMT — CVTRA05Y.cpy:10
    assert store_money(Decimal("42.009"), S9_09_V99) == Decimal("42.00")


def test_rejects_float():
    with pytest.raises(TypeError, match="float"):
        store_money(1.23, S9_09_V99)  # type: ignore[arg-type]


def test_accepts_int_and_str():
    assert store_money(10, S9_09_V99) == Decimal("10.00")
    assert store_money("10.456", S9_09_V99) == Decimal("10.45")


def test_overflow_raises():
    with pytest.raises(OverflowError):
        store_money(Decimal("1000000000.00"), S9_09_V99)  # 10 integer digits
    with pytest.raises(OverflowError):
        store_money(Decimal("10000.00"), S9_04_V99)
