"""Fixed-width records for the five copybooks CBACT04C uses.

Each picture width is the character count in the copybook. ``FILLER`` is
kept so a record written back matches the bytes that were read, including
the zero filler in the category and disclosure exports.

This module only parses and builds records. It does not read or update an
account, so there is no account action to authorize. ``repr`` masks card
numbers, account numbers, customer ids, and other personal fields.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal
from typing import ClassVar, Tuple

from intcalc.zoned import ZonedDecimalError, decode_zoned, encode_zoned

# "x" is PIC X, "9" is PIC 9, "s9" is PIC S9 with an implied decimal scale.
Kind = str


class RecordFormatError(ValueError):
    """A record is the wrong length or a numeric field is not numeric."""


@dataclass(frozen=True)
class Field:
    """One picture in a copybook record.

    ``name`` is the COBOL name. ``attr`` is the Python attribute.
    ``source`` is the copybook line that defines the picture.
    """

    name: str
    attr: str
    kind: Kind
    width: int
    scale: int
    source: str


# Identifiers and free text that can carry an account or card number.
_SENSITIVE = frozenset(
    {
        "trancat_acct_id",
        "acct_id",
        "acct_addr_zip",
        "acct_open_date",
        "acct_expiration_date",
        "acct_reissue_date",
        "xref_card_num",
        "xref_cust_id",
        "xref_acct_id",
        "tran_card_num",
        # TRAN-DESC is built as "Int. for a/c " plus the account id.
        # CBACT04C.cbl lines 485-488. Mask the whole description.
        "tran_desc",
    }
)


def mask_last_four(value: str) -> str:
    """Keep the last four characters. Replace the rest with asterisks."""

    if len(value) <= 4:
        return "*" * len(value)
    return ("*" * (len(value) - 4)) + value[-4:]


class FixedRecord:
    """Common length check, picture validation, and masked ``repr``."""

    LAYOUT: ClassVar[Tuple[Field, ...]] = ()
    RECORD_LENGTH: ClassVar[int] = 0
    RECORD_NAME: ClassVar[str] = "record"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        layout = cls.__dict__.get("LAYOUT")
        if layout is None:
            return
        total = sum(field.width for field in layout)
        length = cls.__dict__.get("RECORD_LENGTH")
        if length is None or total != length:
            raise TypeError(
                f"{cls.__name__} pictures sum to {total}, record length is {length}"
            )

    def __post_init__(self) -> None:
        for field in type(self).LAYOUT:
            raw = getattr(self, field.attr)
            object.__setattr__(self, field.attr, _normalize(field, raw))

    def __repr__(self) -> str:
        parts = []
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name == "filler":
                shown = f"<{len(value)} bytes>"
            elif field.name in _SENSITIVE and isinstance(value, str):
                shown = repr(mask_last_four(value))
            else:
                shown = repr(value)
            parts.append(f"{field.name}={shown}")
        return f"{type(self).__name__}({', '.join(parts)})"

    def to_bytes(self) -> bytes:
        """Encode this record at ``RECORD_LENGTH``."""

        parts = []
        for field in type(self).LAYOUT:
            parts.append(_pack_field(field, getattr(self, field.attr)))
        encoded = "".join(parts).encode("ascii")
        if len(encoded) != type(self).RECORD_LENGTH:
            raise RecordFormatError(
                f"{type(self).RECORD_NAME} must be {type(self).RECORD_LENGTH} bytes, "
                f"got {len(encoded)}"
            )
        return encoded

    @classmethod
    def from_bytes(cls, data: bytes) -> "FixedRecord":
        """Decode one record. Reject the wrong length or a non-numeric field.

        The error names the field and the length. It does not include the
        record bytes, which can hold a card number or account number.
        """

        if not isinstance(data, bytes):
            raise RecordFormatError(f"{cls.RECORD_NAME} must be bytes")
        if len(data) != cls.RECORD_LENGTH:
            raise RecordFormatError(
                f"{cls.RECORD_NAME} must be {cls.RECORD_LENGTH} bytes, got {len(data)}"
            )
        try:
            text = data.decode("ascii")
        except UnicodeDecodeError:
            raise RecordFormatError(f"{cls.RECORD_NAME} is not ASCII") from None

        values = {}
        offset = 0
        for field in cls.LAYOUT:
            chunk = text[offset : offset + field.width]
            offset += field.width
            values[field.attr] = _unpack_field(field, chunk)
        return cls(**values)


def _normalize(field: Field, raw: object) -> object:
    if field.kind == "x":
        return _text(raw, field)
    if field.kind == "9":
        return _digits(raw, field)
    if field.kind == "s9":
        return _store_money(raw, field)
    raise RecordFormatError(f"{field.name} has an unknown picture")


def _store_money(raw: object, field: Field) -> Decimal:
    """Fit a signed picture that is not ROUNDED. Truncate toward zero."""

    try:
        encoded = encode_zoned(raw, field.width, field.scale)
        return decode_zoned(encoded, field.scale)
    except ZonedDecimalError as exc:
        raise RecordFormatError(f"{field.name} does not fit {field.source}") from exc


def _text(raw: object, field: Field) -> str:
    if not isinstance(raw, str):
        raise RecordFormatError(f"{field.name} must be text")
    try:
        raw.encode("ascii")
    except UnicodeEncodeError:
        raise RecordFormatError(f"{field.name} must be single-byte text") from None
    if len(raw) > field.width:
        raise RecordFormatError(f"{field.name} exceeds {field.width} bytes")
    return raw.ljust(field.width)


def _digits(raw: object, field: Field) -> str:
    """PIC 9. Zero-fill on the left. Reject a longer value or any non-digit."""

    if isinstance(raw, bool) or isinstance(raw, float):
        raise RecordFormatError(f"{field.name} is not numeric")
    if isinstance(raw, int):
        if raw < 0:
            raise RecordFormatError(f"{field.name} is not numeric")
        text = str(raw)
    elif isinstance(raw, str):
        text = raw
        if text == "" or not text.isdigit():
            raise RecordFormatError(f"{field.name} is not numeric")
    else:
        raise RecordFormatError(f"{field.name} is not numeric")
    if len(text) > field.width:
        raise RecordFormatError(f"{field.name} exceeds {field.width} digits")
    return text.zfill(field.width)


def _unpack_field(field: Field, chunk: str) -> object:
    if field.kind == "x":
        return chunk
    if field.kind == "9":
        if not chunk.isdigit():
            raise RecordFormatError(f"{field.name} is not numeric")
        return chunk
    if field.kind == "s9":
        try:
            return decode_zoned(chunk, field.scale)
        except ZonedDecimalError:
            raise RecordFormatError(f"{field.name} is not numeric") from None
    raise RecordFormatError(f"{field.name} has an unknown picture")


def _pack_field(field: Field, value: object) -> str:
    if field.kind == "x":
        if not isinstance(value, str) or len(value) != field.width:
            raise RecordFormatError(f"{field.name} must be {field.width} bytes")
        return value
    if field.kind == "9":
        if not isinstance(value, str) or len(value) != field.width or not value.isdigit():
            raise RecordFormatError(f"{field.name} is not numeric")
        return value
    if field.kind == "s9":
        try:
            return encode_zoned(value, field.width, field.scale)
        except ZonedDecimalError:
            raise RecordFormatError(f"{field.name} does not fit {field.source}") from None
    raise RecordFormatError(f"{field.name} has an unknown picture")


@dataclass(frozen=True, repr=False)
class TranCatBalRecord(FixedRecord):
    """TRAN-CAT-BAL-RECORD. CVTRA01Y.cpy lines 4-10. RECLN = 50 (line 2)."""

    trancat_acct_id: str
    trancat_type_cd: str
    trancat_cd: str
    tran_cat_bal: Decimal
    filler: str = " " * 22

    # CVTRA01Y.cpy lines 6-10.
    LAYOUT: ClassVar[Tuple[Field, ...]] = (
        Field("TRANCAT-ACCT-ID", "trancat_acct_id", "9", 11, 0, "CVTRA01Y.cpy line 6 PIC 9(11)"),
        Field("TRANCAT-TYPE-CD", "trancat_type_cd", "x", 2, 0, "CVTRA01Y.cpy line 7 PIC X(02)"),
        Field("TRANCAT-CD", "trancat_cd", "9", 4, 0, "CVTRA01Y.cpy line 8 PIC 9(04)"),
        # Signed, two implied decimals, 11 bytes. Not ROUNDED.
        Field("TRAN-CAT-BAL", "tran_cat_bal", "s9", 11, 2, "CVTRA01Y.cpy line 9 PIC S9(09)V99"),
        Field("FILLER", "filler", "x", 22, 0, "CVTRA01Y.cpy line 10 PIC X(22)"),
    )
    RECORD_LENGTH: ClassVar[int] = 50
    RECORD_NAME: ClassVar[str] = "category balance record"


@dataclass(frozen=True, repr=False)
class CardXrefRecord(FixedRecord):
    """CARD-XREF-RECORD. CVACT03Y.cpy lines 4-8. RECLN 50 (line 2)."""

    xref_card_num: str
    xref_cust_id: str
    xref_acct_id: str
    filler: str = " " * 14

    # CVACT03Y.cpy lines 5-8.
    LAYOUT: ClassVar[Tuple[Field, ...]] = (
        Field("XREF-CARD-NUM", "xref_card_num", "x", 16, 0, "CVACT03Y.cpy line 5 PIC X(16)"),
        Field("XREF-CUST-ID", "xref_cust_id", "9", 9, 0, "CVACT03Y.cpy line 6 PIC 9(09)"),
        Field("XREF-ACCT-ID", "xref_acct_id", "9", 11, 0, "CVACT03Y.cpy line 7 PIC 9(11)"),
        Field("FILLER", "filler", "x", 14, 0, "CVACT03Y.cpy line 8 PIC X(14)"),
    )
    RECORD_LENGTH: ClassVar[int] = 50
    RECORD_NAME: ClassVar[str] = "card cross-reference record"


@dataclass(frozen=True, repr=False)
class DisGroupRecord(FixedRecord):
    """DIS-GROUP-RECORD. CVTRA02Y.cpy lines 4-10. RECLN = 50 (line 2)."""

    dis_acct_group_id: str
    dis_tran_type_cd: str
    dis_tran_cat_cd: str
    dis_int_rate: Decimal
    filler: str = " " * 28

    # CVTRA02Y.cpy lines 6-10.
    LAYOUT: ClassVar[Tuple[Field, ...]] = (
        Field("DIS-ACCT-GROUP-ID", "dis_acct_group_id", "x", 10, 0, "CVTRA02Y.cpy line 6 PIC X(10)"),
        Field("DIS-TRAN-TYPE-CD", "dis_tran_type_cd", "x", 2, 0, "CVTRA02Y.cpy line 7 PIC X(02)"),
        Field("DIS-TRAN-CAT-CD", "dis_tran_cat_cd", "9", 4, 0, "CVTRA02Y.cpy line 8 PIC 9(04)"),
        # Signed rate, two implied decimals, 6 bytes. Not ROUNDED.
        Field("DIS-INT-RATE", "dis_int_rate", "s9", 6, 2, "CVTRA02Y.cpy line 9 PIC S9(04)V99"),
        Field("FILLER", "filler", "x", 28, 0, "CVTRA02Y.cpy line 10 PIC X(28)"),
    )
    RECORD_LENGTH: ClassVar[int] = 50
    RECORD_NAME: ClassVar[str] = "disclosure group record"


@dataclass(frozen=True, repr=False)
class AccountRecord(FixedRecord):
    """ACCOUNT-RECORD. CVACT01Y.cpy lines 4-17. RECLN 300 (line 2)."""

    acct_id: str
    acct_active_status: str
    acct_curr_bal: Decimal
    acct_credit_limit: Decimal
    acct_cash_credit_limit: Decimal
    acct_open_date: str
    # COBOL spells this EXPIRAION. CVACT01Y.cpy line 11.
    acct_expiration_date: str
    acct_reissue_date: str
    acct_curr_cyc_credit: Decimal
    acct_curr_cyc_debit: Decimal
    acct_addr_zip: str
    acct_group_id: str
    filler: str = " " * 178

    # CVACT01Y.cpy lines 5-17. Balance and cycle pictures are S9(10)V99.
    # ADD into ACCT-CURR-BAL is not ROUNDED. CBACT04C.cbl line 352.
    LAYOUT: ClassVar[Tuple[Field, ...]] = (
        Field("ACCT-ID", "acct_id", "9", 11, 0, "CVACT01Y.cpy line 5 PIC 9(11)"),
        Field("ACCT-ACTIVE-STATUS", "acct_active_status", "x", 1, 0, "CVACT01Y.cpy line 6 PIC X(01)"),
        Field("ACCT-CURR-BAL", "acct_curr_bal", "s9", 12, 2, "CVACT01Y.cpy line 7 PIC S9(10)V99"),
        Field("ACCT-CREDIT-LIMIT", "acct_credit_limit", "s9", 12, 2, "CVACT01Y.cpy line 8 PIC S9(10)V99"),
        Field("ACCT-CASH-CREDIT-LIMIT", "acct_cash_credit_limit", "s9", 12, 2, "CVACT01Y.cpy line 9 PIC S9(10)V99"),
        Field("ACCT-OPEN-DATE", "acct_open_date", "x", 10, 0, "CVACT01Y.cpy line 10 PIC X(10)"),
        Field("ACCT-EXPIRAION-DATE", "acct_expiration_date", "x", 10, 0, "CVACT01Y.cpy line 11 PIC X(10)"),
        Field("ACCT-REISSUE-DATE", "acct_reissue_date", "x", 10, 0, "CVACT01Y.cpy line 12 PIC X(10)"),
        Field("ACCT-CURR-CYC-CREDIT", "acct_curr_cyc_credit", "s9", 12, 2, "CVACT01Y.cpy line 13 PIC S9(10)V99"),
        Field("ACCT-CURR-CYC-DEBIT", "acct_curr_cyc_debit", "s9", 12, 2, "CVACT01Y.cpy line 14 PIC S9(10)V99"),
        Field("ACCT-ADDR-ZIP", "acct_addr_zip", "x", 10, 0, "CVACT01Y.cpy line 15 PIC X(10)"),
        Field("ACCT-GROUP-ID", "acct_group_id", "x", 10, 0, "CVACT01Y.cpy line 16 PIC X(10)"),
        Field("FILLER", "filler", "x", 178, 0, "CVACT01Y.cpy line 17 PIC X(178)"),
    )
    RECORD_LENGTH: ClassVar[int] = 300
    RECORD_NAME: ClassVar[str] = "account record"


@dataclass(frozen=True, repr=False)
class TranRecord(FixedRecord):
    """TRAN-RECORD. CVTRA05Y.cpy lines 4-18. RECLN = 350 (line 2)."""

    tran_id: str
    tran_type_cd: str
    tran_cat_cd: str
    tran_source: str
    tran_desc: str
    tran_amt: Decimal
    tran_merchant_id: str
    tran_merchant_name: str
    tran_merchant_city: str
    tran_merchant_zip: str
    tran_card_num: str
    tran_orig_ts: str
    tran_proc_ts: str
    filler: str = " " * 20

    # CVTRA05Y.cpy lines 5-18. TRAN-AMT is S9(09)V99 (line 10), same picture
    # as WS-MONTHLY-INT. CBACT04C.cbl line 168. Not ROUNDED.
    LAYOUT: ClassVar[Tuple[Field, ...]] = (
        Field("TRAN-ID", "tran_id", "x", 16, 0, "CVTRA05Y.cpy line 5 PIC X(16)"),
        Field("TRAN-TYPE-CD", "tran_type_cd", "x", 2, 0, "CVTRA05Y.cpy line 6 PIC X(02)"),
        Field("TRAN-CAT-CD", "tran_cat_cd", "9", 4, 0, "CVTRA05Y.cpy line 7 PIC 9(04)"),
        Field("TRAN-SOURCE", "tran_source", "x", 10, 0, "CVTRA05Y.cpy line 8 PIC X(10)"),
        Field("TRAN-DESC", "tran_desc", "x", 100, 0, "CVTRA05Y.cpy line 9 PIC X(100)"),
        Field("TRAN-AMT", "tran_amt", "s9", 11, 2, "CVTRA05Y.cpy line 10 PIC S9(09)V99"),
        Field("TRAN-MERCHANT-ID", "tran_merchant_id", "9", 9, 0, "CVTRA05Y.cpy line 11 PIC 9(09)"),
        Field("TRAN-MERCHANT-NAME", "tran_merchant_name", "x", 50, 0, "CVTRA05Y.cpy line 12 PIC X(50)"),
        Field("TRAN-MERCHANT-CITY", "tran_merchant_city", "x", 50, 0, "CVTRA05Y.cpy line 13 PIC X(50)"),
        Field("TRAN-MERCHANT-ZIP", "tran_merchant_zip", "x", 10, 0, "CVTRA05Y.cpy line 14 PIC X(10)"),
        Field("TRAN-CARD-NUM", "tran_card_num", "x", 16, 0, "CVTRA05Y.cpy line 15 PIC X(16)"),
        Field("TRAN-ORIG-TS", "tran_orig_ts", "x", 26, 0, "CVTRA05Y.cpy line 16 PIC X(26)"),
        Field("TRAN-PROC-TS", "tran_proc_ts", "x", 26, 0, "CVTRA05Y.cpy line 17 PIC X(26)"),
        Field("FILLER", "filler", "x", 20, 0, "CVTRA05Y.cpy line 18 PIC X(20)"),
    )
    RECORD_LENGTH: ClassVar[int] = 350
    RECORD_NAME: ClassVar[str] = "transaction record"
