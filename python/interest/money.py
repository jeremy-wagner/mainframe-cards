"""COBOL money pictures for CBACT04C.

COMPUTE and ADD in the interest job are not marked ROUNDED, so extra
fractional digits are discarded (truncate toward zero, decimal.ROUND_DOWN).
CBACT04C.cbl 168-169, 464-467.

Never use float. Callers pass Decimal, int, or a decimal string.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Union

MoneyInput = Union[Decimal, int, str]


@dataclass(frozen=True)
class SignedPicture:
    """PIC S9(integer_digits)V followed by `scale` nines.

    Display width is integer_digits + scale. The sign does not add a byte
    in a zoned field; it overlays the last digit.
    """

    integer_digits: int
    scale: int
    source: str

    @property
    def width(self) -> int:
        return self.integer_digits + self.scale

    def store(self, value: MoneyInput) -> Decimal:
        return store_money(value, self.integer_digits, self.scale)


# PIC S9(09)V99.
# WS-MONTHLY-INT and WS-TOTAL-INT: CBACT04C.cbl 168-169.
# COMPUTE / ADD without ROUNDED: CBACT04C.cbl 464-467.
# TRAN-CAT-BAL: CVTRA01Y.cpy 9. TRAN-AMT: CVTRA05Y.cpy 10.
S9_09_V99 = SignedPicture(
    integer_digits=9,
    scale=2,
    source="CBACT04C.cbl 168-169, 464-467; CVTRA01Y.cpy 9; CVTRA05Y.cpy 10",
)

# PIC S9(04)V99. DIS-INT-RATE. CVTRA02Y.cpy 9.
S9_04_V99 = SignedPicture(
    integer_digits=4,
    scale=2,
    source="CVTRA02Y.cpy 9",
)

# PIC S9(10)V99. Account balances and cycle totals. CVACT01Y.cpy 7-9, 13-14.
S9_10_V99 = SignedPicture(
    integer_digits=10,
    scale=2,
    source="CVACT01Y.cpy 7-9, 13-14",
)


def store_money(value: MoneyInput, integer_digits: int, scale: int) -> Decimal:
    """Store a signed amount in a COBOL picture that is not ROUNDED.

    Fractional digits past `scale` are dropped toward zero (ROUND_DOWN).
    CBACT04C.cbl 168-169 and 464-467. A value that still does not fit the
    integer digits is rejected.
    """

    amount = _as_decimal(value)
    quantum = Decimal(1).scaleb(-scale)
    truncated = amount.quantize(quantum, rounding=ROUND_DOWN)
    integral = truncated.copy_abs().to_integral_value(rounding=ROUND_DOWN)
    if integral >= Decimal(10) ** integer_digits:
        raise ValueError(
            f"amount does not fit PIC S9({integer_digits})V{'9' * scale}"
        )
    return truncated


def _as_decimal(value: MoneyInput) -> Decimal:
    # bool is a subclass of int; reject it with float so True cannot become 1.
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
            raise ValueError("money must be a finite decimal amount") from None
    else:
        raise TypeError("money must be decimal.Decimal, never float")
    if not amount.is_finite():
        raise ValueError("money must be a finite decimal amount")
    return amount
