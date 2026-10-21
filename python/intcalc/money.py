"""COBOL picture storage for INTCALC money and rate fields.

COMPUTE without ROUNDED truncates into the receiving picture
(CBACT04C.cbl:464-465). Project rule: non-ROUNDED → Decimal ROUND_DOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Union

NumberLike = Union[Decimal, int, str]


@dataclass(frozen=True, slots=True)
class SignedPicture:
    """Signed numeric picture: PIC S9(integer_digits)V9(fractional_digits)."""

    integer_digits: int
    fractional_digits: int

    def __post_init__(self) -> None:
        if self.integer_digits < 1 or self.fractional_digits < 0:
            raise ValueError("invalid picture dimensions")

    @property
    def quantum(self) -> Decimal:
        return Decimal("1").scaleb(-self.fractional_digits)

    @property
    def max_abs(self) -> Decimal:
        # Largest magnitude storable: integer_digits nines, then fractional digits.
        return Decimal("9" * self.integer_digits + "." + "9" * self.fractional_digits)


# WS-MONTHLY-INT / WS-TOTAL-INT — CBACT04C.cbl:168-169
# TRAN-CAT-BAL — CVTRA01Y.cpy:9
# TRAN-AMT — CVTRA05Y.cpy:10
S9_09_V99 = SignedPicture(9, 2)

# DIS-INT-RATE — CVTRA02Y.cpy:9
S9_04_V99 = SignedPicture(4, 2)

# ACCT-CURR-BAL, ACCT-CREDIT-LIMIT, ACCT-CASH-CREDIT-LIMIT,
# ACCT-CURR-CYC-CREDIT, ACCT-CURR-CYC-DEBIT — CVACT01Y.cpy:7-9, 13-14
S9_10_V99 = SignedPicture(10, 2)


def store_money(value: NumberLike | float, picture: SignedPicture) -> Decimal:
    """Store *value* into *picture*, truncating excess fractional digits.

    Matches COMPUTE without ROUNDED into a V99 field (CBACT04C.cbl:464-465).
    Rejects float so binary floating-point cannot enter money paths.
    """
    if isinstance(value, float):
        raise TypeError("float is not allowed for money; use Decimal")

    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, str):
        amount = Decimal(value)
    else:
        raise TypeError(f"unsupported money type: {type(value)!r}")

    # Non-ROUNDED COBOL store → truncate (ROUND_DOWN). CBACT04C.cbl:464-465
    stored = amount.quantize(picture.quantum, rounding=ROUND_DOWN)

    if abs(stored) > picture.max_abs:
        raise OverflowError(
            f"{stored} exceeds PIC S9({picture.integer_digits})"
            f"V9({picture.fractional_digits}) capacity {picture.max_abs}"
        )
    return stored
