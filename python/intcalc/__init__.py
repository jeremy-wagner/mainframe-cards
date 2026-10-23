"""Record layouts and zoned-decimal codec for the CBACT04C interest batch.

Source program: app/cbl/CBACT04C.cbl. Copybooks live under app/cpy/.
Money is decimal.Decimal. Pictures without ROUNDED truncate toward zero.
"""

from intcalc.records import (
    AccountRecord,
    CardXrefRecord,
    DisGroupRecord,
    RecordFormatError,
    TranCatBalRecord,
    TranRecord,
)
from intcalc.textfile import read_records, reserialize
from intcalc.zoned import ZonedDecimalError, decode_zoned, encode_zoned

__all__ = [
    "AccountRecord",
    "CardXrefRecord",
    "DisGroupRecord",
    "RecordFormatError",
    "TranCatBalRecord",
    "TranRecord",
    "ZonedDecimalError",
    "decode_zoned",
    "encode_zoned",
    "read_records",
    "reserialize",
]
