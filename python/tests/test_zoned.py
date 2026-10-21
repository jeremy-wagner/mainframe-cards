"""Round trips for the signed amounts the interest job reads and writes."""

from decimal import Decimal
from pathlib import Path

import pytest

from intcalc.zoned import ZonedDecimalError, fit, format_zoned, parse_zoned

REPO = Path(__file__).resolve().parents[2]
ASCII = REPO / "app" / "data" / "ASCII"

# PIC S9(09)V99, CVTRA01Y.cpy line 9 and CVTRA05Y.cpy line 10.
BAL = (9, 2)
# PIC S9(04)V99, CVTRA02Y.cpy line 9.
RATE = (4, 2)
# PIC S9(10)V99, CVACT01Y.cpy lines 7, 13 and 14.
ACCT = (10, 2)


def test_overpunch_digit_table():
    positive = "{ABCDEFGHI"
    negative = "}JKLMNOPQR"
    for digit, pos, neg in zip("0123456789", positive, negative):
        assert parse_zoned(pos, 1, 0, True) == Decimal(digit)
        assert parse_zoned(neg, 1, 0, True) == -Decimal(digit)
        assert format_zoned(Decimal(digit), 1, 0, True) == pos
        # -Decimal(0) is not a signed zero; copy_negate is.
        assert format_zoned(Decimal(digit).copy_negate(), 1, 0, True) == neg


def test_round_trip_zero_negative_and_max():
    cases = [
        (Decimal("0.00"), "0000000000{"),
        (Decimal("-0.00"), "0000000000}"),
        (Decimal("1.20"), "0000000012{"),
        (Decimal("-1.23"), "0000000012L"),
        (Decimal("999999999.99"), "9999999999I"),
        (Decimal("-999999999.99"), "9999999999R"),
    ]
    for value, text in cases:
        assert format_zoned(value, *BAL, True) == text
        assert parse_zoned(text, *BAL, True) == value
        assert format_zoned(parse_zoned(text, *BAL, True), *BAL, True) == text


def test_plain_trailing_digit_is_positive():
    assert parse_zoned("00000000120", *BAL, True) == Decimal("1.20")
    assert format_zoned(parse_zoned("00000000120", *BAL, True), *BAL, True) == "0000000012{"


def test_fractional_truncation_is_toward_zero():
    # No ROUNDED on the interest COMPUTE. CBACT04C.cbl lines 464-466.
    assert fit(Decimal("1.239"), *BAL) == Decimal("1.23")
    assert fit(Decimal("-1.239"), *BAL) == Decimal("-1.23")
    assert fit(Decimal("0.009"), *BAL) == Decimal("0.00")
    assert fit(Decimal("-0.009"), *BAL) == Decimal("-0.00")
    assert fit(Decimal("-0.009"), *BAL).is_signed()


def test_high_order_digits_are_dropped():
    # No ON SIZE ERROR. CBACT04C.cbl lines 352, 464 and 466.
    assert fit(Decimal("10000000000.999"), *BAL) == Decimal("0.99")
    assert fit(Decimal("-10000000000.999"), *BAL) == Decimal("-0.99")
    assert fit(Decimal("9999999999.99"), *BAL) == Decimal("999999999.99")
    assert format_zoned(Decimal("10000000000.999"), *BAL, True) == "0000000009I"


def test_account_and_rate_pictures():
    # 194.00 is 12 characters in PIC S9(10)V99: ten integer digits, two decimals.
    assert format_zoned(Decimal("194.00"), *ACCT, True) == "00000001940{"
    assert format_zoned(Decimal("15.00"), *RATE, True) == "00150{"
    assert parse_zoned("00150{", *RATE, True) == Decimal("15.00")
    assert format_zoned(Decimal("-15.09"), *RATE, True) == "00150R"


def test_sample_files_match_the_pictures():
    balance = (ASCII / "tcatbal.txt").read_text().splitlines()[0][17:28]
    rate = (ASCII / "discgrp.txt").read_text().splitlines()[0][16:22]
    current = (ASCII / "acctdata.txt").read_text().splitlines()[0][12:24]
    assert parse_zoned(balance, *BAL, True) == Decimal("0.00")
    assert parse_zoned(rate, *RATE, True) == Decimal("15.00")
    assert parse_zoned(current, *ACCT, True) == Decimal("194.00")


def test_unsigned_field_rejects_a_negative_amount():
    assert format_zoned(Decimal("11"), 11, 0, False) == "00000000011"
    assert parse_zoned("00000000011", 11, 0, False) == Decimal("11")
    with pytest.raises(ZonedDecimalError):
        format_zoned(Decimal("-1"), 11, 0, False)
    with pytest.raises(ZonedDecimalError):
        parse_zoned("0000000001J", 11, 0, False)


@pytest.mark.parametrize(
    "value",
    [1.5, True, "1.20", Decimal("NaN"), Decimal("Infinity")],
)
def test_rejects_non_decimal_amounts(value):
    with pytest.raises(ZonedDecimalError):
        fit(value, *BAL)


def test_rejects_bad_fields():
    with pytest.raises(ZonedDecimalError):
        parse_zoned("0000000000{", 9, 1, True)
    with pytest.raises(ZonedDecimalError):
        parse_zoned("0000000000*", *BAL, True)
    with pytest.raises(ZonedDecimalError):
        parse_zoned(" 000000000{", *BAL, True)
    with pytest.raises(ZonedDecimalError):
        fit(Decimal("1"), -1, 2)
    with pytest.raises(ZonedDecimalError):
        fit(Decimal("1"), True, 2)
