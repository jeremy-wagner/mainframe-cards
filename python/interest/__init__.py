"""In-memory types for the CBACT04C interest batch.

Source program: app/cbl/CBACT04C.cbl. Copybooks live under app/cpy/.
Money is decimal.Decimal. Fields without ROUNDED truncate toward zero.
"""

from interest.money import S9_04_V99, S9_09_V99, S9_10_V99, store_money
from interest.records import (
    AccountRecord,
    CardXrefRecord,
    DisGroupRecord,
    TranCatBalRecord,
    TranRecord,
)

__all__ = [
    "AccountRecord",
    "CardXrefRecord",
    "DisGroupRecord",
    "S9_04_V99",
    "S9_09_V99",
    "S9_10_V99",
    "TranCatBalRecord",
    "TranRecord",
    "store_money",
]
