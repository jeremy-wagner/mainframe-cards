"""COBOL picture-compatible money storage using Decimal.

CBACT04C interest COMPUTE has no ROUNDED clause (CBACT04C.cbl 464-465), so
fractional digits beyond the target scale are truncated (ROUND_DOWN), not
rounded half-up.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True)
class SignedPicture:
    """Signed COBOL numeric with implied decimal (PIC S9(n)V99)."""

    integer_digits: int
    scale: int = 2

    @property
    def quantize_exp(self) -> Decimal:
        return Decimal("1").scaleb(-self.scale)


# TRAN-CAT-BAL / WS-MONTHLY-INT / TRAN-AMT — CVTRA01Y.cpy 9, CVTRA05Y.cpy 10;
# WS-MONTHLY-INT target of COMPUTE at CBACT04C.cbl 464-465.
S9_09_V99 = SignedPicture(integer_digits=9, scale=2)

# DIS-INT-RATE — CVTRA02Y.cpy 9.
S9_04_V99 = SignedPicture(integer_digits=4, scale=2)

# ACCT-CURR-BAL and related account money fields — CVACT01Y.cpy 7-14.
S9_10_V99 = SignedPicture(integer_digits=10, scale=2)


def store_money(value: Decimal, picture: SignedPicture) -> Decimal:
    """Store *value* into a COBOL signed picture without ROUNDED.

    Truncates toward zero to *picture.scale* fractional digits
    (ROUND_DOWN), matching COMPUTE without ROUNDED at CBACT04C.cbl 464-465.
    """
    if not isinstance(value, Decimal):
        raise TypeError("money values must be decimal.Decimal, not float")
    quantized = value.quantize(picture.quantize_exp, rounding=ROUND_DOWN)
    max_abs = Decimal(10) ** picture.integer_digits - picture.quantize_exp
    if abs(quantized) > max_abs:
        raise OverflowError(
            f"{quantized} does not fit PIC S9({picture.integer_digits})"
            f"V{('9' * picture.scale)}"
        )
    return quantized
