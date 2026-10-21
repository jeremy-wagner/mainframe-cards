"""ASCII zoned decimal for the signed pictures in the interest copybooks.

COBOL ``PIC S9`` without ``SIGN LEADING`` keeps the sign in the last digit
(trailing overpunch). The exports in ``app/data/ASCII`` use the ASCII
overpunch, not EBCDIC zones:

    positive 0-9  { A B C D E F G H I
    negative 0-9  } J K L M N O P Q R

The implied decimal point is not stored. ``S9(09)V99`` is 11 digits with
the point two places from the right (CVTRA01Y.cpy line 9). None of these
pictures are ``ROUNDED``, so a value with extra fractional digits is
truncated toward zero (``ROUND_DOWN``).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Union

# Trailing overpunch. Last digit only. See module docstring.
_POSITIVE = "{ABCDEFGHI"
_NEGATIVE = "}JKLMNOPQR"

MoneyInput = Union[Decimal, int, str]


class ZonedDecimalError(ValueError):
    """A signed numeric field is not a zoned decimal or does not fit."""


def decode_zoned(raw: str, scale: int) -> Decimal:
    """Decode a trailing-overpunch zoned field to ``Decimal``.

    ``scale`` is the number of implied decimal digits (the ``V99`` in the
    picture). A plain last digit is the unsigned zone and means positive.
    """

    if not isinstance(raw, str) or scale < 0 or scale > len(raw) or raw == "":
        raise ZonedDecimalError("zoned decimal is not numeric")

    sign, last = _last_digit(raw[-1])
    body = raw[:-1]
    if not body.isdigit():
        raise ZonedDecimalError("zoned decimal is not numeric")

    digits = body + last
    if scale:
        text = digits[:-scale] + "." + digits[-scale:]
    else:
        text = digits or "0"
    if sign < 0:
        text = "-" + text
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ZonedDecimalError("zoned decimal is not numeric") from None
    if not amount.is_finite():
        raise ZonedDecimalError("zoned decimal is not numeric")
    return amount


def encode_zoned(value: MoneyInput, width: int, scale: int) -> str:
    """Encode ``value`` as ``width`` zoned digits with trailing overpunch.

    Extra fractional digits are truncated toward zero because the pictures
    are not ``ROUNDED``. A result that still does not fit ``width`` is
    rejected. Positive and negative zero stay distinct (``{`` versus ``}``).
    """

    if width < 1 or scale < 0 or scale > width:
        raise ZonedDecimalError("zoned decimal picture is invalid")

    amount = _as_decimal(value)
    quantum = Decimal(1).scaleb(-scale)
    truncated = amount.quantize(quantum, rounding=ROUND_DOWN)
    negative = truncated.is_signed()
    rendered = format(abs(truncated), "f")
    whole, _, frac = rendered.partition(".")
    frac = (frac + ("0" * scale))[:scale]
    digits = whole + frac
    if len(digits) > width:
        raise ZonedDecimalError("amount does not fit the zoned picture")
    digits = digits.zfill(width)
    overpunch = _NEGATIVE if negative else _POSITIVE
    return digits[:-1] + overpunch[int(digits[-1])]


def _last_digit(char: str) -> tuple[int, str]:
    positive = _POSITIVE.find(char)
    if positive >= 0:
        return 1, str(positive)
    negative = _NEGATIVE.find(char)
    if negative >= 0:
        return -1, str(negative)
    if char.isdigit():
        return 1, char
    raise ZonedDecimalError("zoned decimal is not numeric")


def _as_decimal(value: MoneyInput) -> Decimal:
    # bool is a subclass of int. Reject it with float so True cannot become 1.
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("money must be decimal.Decimal, never float")
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, str):
        try:
            amount = Decimal(value)
        except InvalidOperation:
            raise ZonedDecimalError("money must be a finite decimal amount") from None
    else:
        raise TypeError("money must be decimal.Decimal, never float")
    if not amount.is_finite():
        raise ZonedDecimalError("money must be a finite decimal amount")
    return amount
