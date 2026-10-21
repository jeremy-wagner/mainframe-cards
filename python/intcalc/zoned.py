"""ASCII zoned decimal, the display form of the signed amounts in this job.

The last character carries the sign (overpunch). Positive digits are
``{ABCDEFGHI`` and negative digits are ``}JKLMNOPQR``. A plain ``0``-``9``
in the last position is a positive value, which is the unsigned zone.

Pictures this module serves:

* ``PIC S9(09)V99`` ``TRAN-CAT-BAL``, ``app/cpy/CVTRA01Y.cpy`` line 9.
* ``PIC S9(04)V99`` ``DIS-INT-RATE``, ``app/cpy/CVTRA02Y.cpy`` line 9.
* ``PIC S9(10)V99`` ``ACCT-CURR-BAL``, ``app/cpy/CVACT01Y.cpy`` line 7.
* ``PIC S9(10)V99`` ``ACCT-CURR-CYC-CREDIT`` and ``ACCT-CURR-CYC-DEBIT``,
  ``app/cpy/CVACT01Y.cpy`` lines 13-14.
* ``PIC S9(09)V99`` ``TRAN-AMT``, ``app/cpy/CVTRA05Y.cpy`` line 10.

``digits`` is the count of digits before the decimal point (the ``9`` in
``S9(9)``) and ``scale`` is the count after it (``V99`` is 2). The field
is ``digits + scale`` characters wide.
"""

from decimal import Decimal, ROUND_DOWN

# COBOL numeric display items cannot exceed 31 digits.
_MAX_DIGITS = 31

_POSITIVE = {"{": 0, "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8, "I": 9}
_NEGATIVE = {"}": 0, "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "O": 6, "P": 7, "Q": 8, "R": 9}
_POSITIVE_CHAR = "{ABCDEFGHI"
_NEGATIVE_CHAR = "}JKLMNOPQR"


class ZonedDecimalError(ValueError):
    """A field is not a valid zoned decimal of the picture it was given."""


def fit(value: Decimal, digits: int, scale: int) -> Decimal:
    """Truncate ``value`` into a ``PIC S9(digits)V9(scale)`` receiving field.

    Extra fractional digits are dropped toward zero. There is no ``ROUNDED``
    on the interest result or on the add into the current balance
    (``app/cbl/CBACT04C.cbl`` lines 464-466 and 352), so this is ``ROUND_DOWN``.
    Digits that do not fit to the left of the decimal are dropped with no
    error, which is what those statements do with no ``ON SIZE ERROR``.
    A negative amount that truncates to zero stays negative.
    """
    _check_picture(digits, scale)
    if type(value) is not Decimal or not value.is_finite():
        raise ZonedDecimalError("amount must be a finite decimal")

    quantum = Decimal(10) ** -scale
    # Fractional truncation toward zero. CBACT04C.cbl lines 464-466, 352.
    truncated = value.quantize(quantum, rounding=ROUND_DOWN)
    negative = truncated.is_signed()
    width = digits + scale
    scaled = (abs(truncated) * (Decimal(10) ** scale)).to_integral_value(rounding=ROUND_DOWN)
    # High-order digits are lost. CBACT04C.cbl lines 352, 464 and 466.
    scaled = scaled % (Decimal(10) ** width)
    fitted = scaled / (Decimal(10) ** scale)
    if negative:
        fitted = fitted.copy_negate()
    return fitted.quantize(quantum)


def parse_zoned(text: str, digits: int, scale: int, signed: bool) -> Decimal:
    """Read one zoned-decimal field into a ``Decimal``."""
    _check_picture(digits, scale)
    if type(signed) is not bool:
        raise ZonedDecimalError("signed must be true or false")
    width = digits + scale
    if type(text) is not str or len(text) != width:
        raise ZonedDecimalError(f"zoned field must be {width} characters")

    last = text[-1]
    body = text[:-1]
    if body and not body.isdigit():
        raise ZonedDecimalError("zoned field has a non-digit before the sign")

    if signed and last in _NEGATIVE:
        negative = True
        digit = _NEGATIVE[last]
    elif last in _POSITIVE or last.isdigit():
        negative = False
        digit = _POSITIVE[last] if last in _POSITIVE else int(last)
    else:
        raise ZonedDecimalError("zoned field has an invalid sign digit")

    scaled = int(body) * 10 + digit if body else digit
    value = Decimal(scaled) / (Decimal(10) ** scale)
    if negative:
        value = value.copy_negate()
    return value.quantize(Decimal(10) ** -scale)


def format_zoned(value: Decimal, digits: int, scale: int, signed: bool) -> str:
    """Write a ``Decimal`` as a zoned-decimal field of exactly ``digits + scale`` characters.

    Signed fields always use overpunch, including ``{`` for positive zero
    and ``}`` for negative zero. Unsigned fields are plain digits.
    """
    if type(signed) is not bool:
        raise ZonedDecimalError("signed must be true or false")
    fitted = fit(value, digits, scale)
    if fitted.is_signed() and not signed:
        raise ZonedDecimalError("unsigned field cannot hold a negative amount")

    width = digits + scale
    scaled = (abs(fitted) * (Decimal(10) ** scale)).to_integral_value(rounding=ROUND_DOWN)
    raw = f"{int(scaled):0{width}d}"
    if not signed:
        return raw
    table = _NEGATIVE_CHAR if fitted.is_signed() else _POSITIVE_CHAR
    return raw[:-1] + table[int(raw[-1])]


def _check_picture(digits: int, scale: int) -> None:
    if type(digits) is not int or type(scale) is not int:
        raise ZonedDecimalError("digits and scale must be integers")
    if digits < 0 or scale < 0 or digits + scale < 1 or digits + scale > _MAX_DIGITS:
        raise ZonedDecimalError("picture must have between 1 and 31 digits")
