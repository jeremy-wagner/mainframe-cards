"""In-memory copies of the five copybooks CBACT04C reads and writes.

Widths are character positions from the copybooks (RECLN in the comment
header of each file). FILLER is counted in PICTURES so the sum is the
record length; it is not a caller-supplied field.

Text is PIC X: space-padded on the right, rejected when longer.
Unsigned numbers are PIC 9: zero-padded on the left.
Money is stored with store_money (ROUND_DOWN). See money.py.

repr masks card numbers, account numbers, customer ids, and the account
ZIP. Full values stay on the object for the batch; they must not be logged.
"""

from dataclasses import dataclass, fields
from decimal import Decimal
from typing import ClassVar, Sequence, Tuple

from interest.money import S9_04_V99, S9_09_V99, S9_10_V99

Picture = Tuple[str, int]

# Names whose display form must not include the full value.
_SENSITIVE = frozenset(
    {
        "trancat_acct_id",
        "acct_id",
        "acct_addr_zip",
        "xref_card_num",
        "xref_cust_id",
        "xref_acct_id",
        "tran_card_num",
        # TRAN-DESC embeds the account id. CBACT04C.cbl 485-488.
        "tran_desc",
        "acct_open_date",
        "acct_expiration_date",
        "acct_reissue_date",
    }
)


def mask_last_four(value: str) -> str:
    """Keep the last four characters and replace the rest with asterisks."""

    if len(value) <= 4:
        return "*" * len(value)
    return ("*" * (len(value) - 4)) + value[-4:]


def _width(pictures: Sequence[Picture], name: str) -> int:
    for picture_name, width in pictures:
        if picture_name == name:
            return width
    raise KeyError(name)


def require_text(value: str, width: int, field: str) -> str:
    """PIC X(width). Space-fill on the right. Reject a longer value."""

    if not isinstance(value, str):
        raise TypeError(f"{field} must be str")
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError(f"{field} must be single-byte text") from None
    if len(value) > width:
        raise ValueError(f"{field} exceeds PIC X({width})")
    return value.ljust(width)


def require_digits(value: object, width: int, field: str) -> str:
    """PIC 9(width). Zero-fill on the left. Reject a longer value."""

    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{field} must be an unsigned integer or digit string")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"{field} must be unsigned")
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            raise ValueError(f"{field} must be digits")
    else:
        raise TypeError(f"{field} must be an unsigned integer or digit string")
    if len(text) > width:
        raise ValueError(f"{field} exceeds PIC 9({width})")
    return text.zfill(width)


class _MaskedRecord:
    def __repr__(self) -> str:
        parts = []
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in _SENSITIVE and isinstance(value, str):
                shown = mask_last_four(value)
            else:
                shown = repr(value)
            parts.append(f"{field.name}={shown}")
        return f"{type(self).__name__}({', '.join(parts)})"


@dataclass(frozen=True, repr=False)
class TranCatBalRecord(_MaskedRecord):
    """TRAN-CAT-BAL-RECORD. CVTRA01Y.cpy 4-10. RECLN = 50 (line 2)."""

    trancat_acct_id: str
    trancat_type_cd: str
    trancat_cd: str
    tran_cat_bal: Decimal

    # CVTRA01Y.cpy 6-10.
    PICTURES: ClassVar[Tuple[Picture, ...]] = (
        ("TRANCAT-ACCT-ID", 11),
        ("TRANCAT-TYPE-CD", 2),
        ("TRANCAT-CD", 4),
        ("TRAN-CAT-BAL", S9_09_V99.width),
        ("FILLER", 22),
    )
    RECORD_LENGTH: ClassVar[int] = 50

    def __post_init__(self) -> None:
        # CVTRA01Y.cpy 6. PIC 9(11).
        object.__setattr__(
            self,
            "trancat_acct_id",
            require_digits(self.trancat_acct_id, _width(self.PICTURES, "TRANCAT-ACCT-ID"), "TRANCAT-ACCT-ID"),
        )
        # CVTRA01Y.cpy 7. PIC X(02).
        object.__setattr__(
            self,
            "trancat_type_cd",
            require_text(self.trancat_type_cd, _width(self.PICTURES, "TRANCAT-TYPE-CD"), "TRANCAT-TYPE-CD"),
        )
        # CVTRA01Y.cpy 8. PIC 9(04).
        object.__setattr__(
            self,
            "trancat_cd",
            require_digits(self.trancat_cd, _width(self.PICTURES, "TRANCAT-CD"), "TRANCAT-CD"),
        )
        # CVTRA01Y.cpy 9. PIC S9(09)V99. Not ROUNDED. CBACT04C.cbl 464-465.
        object.__setattr__(self, "tran_cat_bal", S9_09_V99.store(self.tran_cat_bal))


@dataclass(frozen=True, repr=False)
class DisGroupRecord(_MaskedRecord):
    """DIS-GROUP-RECORD. CVTRA02Y.cpy 4-10. RECLN = 50 (line 2)."""

    dis_acct_group_id: str
    dis_tran_type_cd: str
    dis_tran_cat_cd: str
    dis_int_rate: Decimal

    # CVTRA02Y.cpy 6-10.
    PICTURES: ClassVar[Tuple[Picture, ...]] = (
        ("DIS-ACCT-GROUP-ID", 10),
        ("DIS-TRAN-TYPE-CD", 2),
        ("DIS-TRAN-CAT-CD", 4),
        ("DIS-INT-RATE", S9_04_V99.width),
        ("FILLER", 28),
    )
    RECORD_LENGTH: ClassVar[int] = 50

    def __post_init__(self) -> None:
        # CVTRA02Y.cpy 6. PIC X(10). MOVE 'DEFAULT' occupies 7 bytes and
        # leaves three spaces. The fallback itself is CBACT04C.cbl 436-438.
        object.__setattr__(
            self,
            "dis_acct_group_id",
            require_text(self.dis_acct_group_id, _width(self.PICTURES, "DIS-ACCT-GROUP-ID"), "DIS-ACCT-GROUP-ID"),
        )
        # CVTRA02Y.cpy 7. PIC X(02).
        object.__setattr__(
            self,
            "dis_tran_type_cd",
            require_text(self.dis_tran_type_cd, _width(self.PICTURES, "DIS-TRAN-TYPE-CD"), "DIS-TRAN-TYPE-CD"),
        )
        # CVTRA02Y.cpy 8. PIC 9(04).
        object.__setattr__(
            self,
            "dis_tran_cat_cd",
            require_digits(self.dis_tran_cat_cd, _width(self.PICTURES, "DIS-TRAN-CAT-CD"), "DIS-TRAN-CAT-CD"),
        )
        # CVTRA02Y.cpy 9. PIC S9(04)V99.
        object.__setattr__(self, "dis_int_rate", S9_04_V99.store(self.dis_int_rate))


@dataclass(frozen=True, repr=False)
class AccountRecord(_MaskedRecord):
    """ACCOUNT-RECORD. CVACT01Y.cpy 4-17. RECLN 300 (line 2)."""

    acct_id: str
    acct_active_status: str
    acct_curr_bal: Decimal
    acct_credit_limit: Decimal
    acct_cash_credit_limit: Decimal
    acct_open_date: str
    # COBOL name is ACCT-EXPIRAION-DATE. CVACT01Y.cpy 11.
    acct_expiration_date: str
    acct_reissue_date: str
    acct_curr_cyc_credit: Decimal
    acct_curr_cyc_debit: Decimal
    acct_addr_zip: str
    acct_group_id: str

    # CVACT01Y.cpy 5-17.
    PICTURES: ClassVar[Tuple[Picture, ...]] = (
        ("ACCT-ID", 11),
        ("ACCT-ACTIVE-STATUS", 1),
        ("ACCT-CURR-BAL", S9_10_V99.width),
        ("ACCT-CREDIT-LIMIT", S9_10_V99.width),
        ("ACCT-CASH-CREDIT-LIMIT", S9_10_V99.width),
        ("ACCT-OPEN-DATE", 10),
        ("ACCT-EXPIRAION-DATE", 10),
        ("ACCT-REISSUE-DATE", 10),
        ("ACCT-CURR-CYC-CREDIT", S9_10_V99.width),
        ("ACCT-CURR-CYC-DEBIT", S9_10_V99.width),
        ("ACCT-ADDR-ZIP", 10),
        ("ACCT-GROUP-ID", 10),
        ("FILLER", 178),
    )
    RECORD_LENGTH: ClassVar[int] = 300

    def __post_init__(self) -> None:
        pictures = self.PICTURES
        # CVACT01Y.cpy 5. PIC 9(11).
        object.__setattr__(self, "acct_id", require_digits(self.acct_id, _width(pictures, "ACCT-ID"), "ACCT-ID"))
        # CVACT01Y.cpy 6. PIC X(01).
        object.__setattr__(
            self,
            "acct_active_status",
            require_text(self.acct_active_status, _width(pictures, "ACCT-ACTIVE-STATUS"), "ACCT-ACTIVE-STATUS"),
        )
        # CVACT01Y.cpy 7, 8, 9, 13, 14. PIC S9(10)V99. ADD at CBACT04C.cbl 352 has no ROUNDED.
        object.__setattr__(self, "acct_curr_bal", S9_10_V99.store(self.acct_curr_bal))
        object.__setattr__(self, "acct_credit_limit", S9_10_V99.store(self.acct_credit_limit))
        object.__setattr__(self, "acct_cash_credit_limit", S9_10_V99.store(self.acct_cash_credit_limit))
        # CVACT01Y.cpy 10. PIC X(10).
        object.__setattr__(
            self,
            "acct_open_date",
            require_text(self.acct_open_date, _width(pictures, "ACCT-OPEN-DATE"), "ACCT-OPEN-DATE"),
        )
        # CVACT01Y.cpy 11. PIC X(10). Spelled EXPIRAION in the copybook.
        object.__setattr__(
            self,
            "acct_expiration_date",
            require_text(self.acct_expiration_date, _width(pictures, "ACCT-EXPIRAION-DATE"), "ACCT-EXPIRAION-DATE"),
        )
        # CVACT01Y.cpy 12. PIC X(10).
        object.__setattr__(
            self,
            "acct_reissue_date",
            require_text(self.acct_reissue_date, _width(pictures, "ACCT-REISSUE-DATE"), "ACCT-REISSUE-DATE"),
        )
        object.__setattr__(self, "acct_curr_cyc_credit", S9_10_V99.store(self.acct_curr_cyc_credit))
        object.__setattr__(self, "acct_curr_cyc_debit", S9_10_V99.store(self.acct_curr_cyc_debit))
        # CVACT01Y.cpy 15. PIC X(10).
        object.__setattr__(
            self,
            "acct_addr_zip",
            require_text(self.acct_addr_zip, _width(pictures, "ACCT-ADDR-ZIP"), "ACCT-ADDR-ZIP"),
        )
        # CVACT01Y.cpy 16. PIC X(10).
        object.__setattr__(
            self,
            "acct_group_id",
            require_text(self.acct_group_id, _width(pictures, "ACCT-GROUP-ID"), "ACCT-GROUP-ID"),
        )


@dataclass(frozen=True, repr=False)
class CardXrefRecord(_MaskedRecord):
    """CARD-XREF-RECORD. CVACT03Y.cpy 4-8. RECLN 50 (line 2)."""

    xref_card_num: str
    xref_cust_id: str
    xref_acct_id: str

    # CVACT03Y.cpy 5-8.
    PICTURES: ClassVar[Tuple[Picture, ...]] = (
        ("XREF-CARD-NUM", 16),
        ("XREF-CUST-ID", 9),
        ("XREF-ACCT-ID", 11),
        ("FILLER", 14),
    )
    RECORD_LENGTH: ClassVar[int] = 50

    def __post_init__(self) -> None:
        pictures = self.PICTURES
        # CVACT03Y.cpy 5. PIC X(16).
        object.__setattr__(
            self,
            "xref_card_num",
            require_text(self.xref_card_num, _width(pictures, "XREF-CARD-NUM"), "XREF-CARD-NUM"),
        )
        # CVACT03Y.cpy 6. PIC 9(09).
        object.__setattr__(
            self,
            "xref_cust_id",
            require_digits(self.xref_cust_id, _width(pictures, "XREF-CUST-ID"), "XREF-CUST-ID"),
        )
        # CVACT03Y.cpy 7. PIC 9(11).
        object.__setattr__(
            self,
            "xref_acct_id",
            require_digits(self.xref_acct_id, _width(pictures, "XREF-ACCT-ID"), "XREF-ACCT-ID"),
        )


@dataclass(frozen=True, repr=False)
class TranRecord(_MaskedRecord):
    """TRAN-RECORD. CVTRA05Y.cpy 4-18. RECLN = 350 (line 2)."""

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

    # CVTRA05Y.cpy 5-18.
    PICTURES: ClassVar[Tuple[Picture, ...]] = (
        ("TRAN-ID", 16),
        ("TRAN-TYPE-CD", 2),
        ("TRAN-CAT-CD", 4),
        ("TRAN-SOURCE", 10),
        ("TRAN-DESC", 100),
        ("TRAN-AMT", S9_09_V99.width),
        ("TRAN-MERCHANT-ID", 9),
        ("TRAN-MERCHANT-NAME", 50),
        ("TRAN-MERCHANT-CITY", 50),
        ("TRAN-MERCHANT-ZIP", 10),
        ("TRAN-CARD-NUM", 16),
        ("TRAN-ORIG-TS", 26),
        ("TRAN-PROC-TS", 26),
        ("FILLER", 20),
    )
    RECORD_LENGTH: ClassVar[int] = 350

    def __post_init__(self) -> None:
        pictures = self.PICTURES
        # CVTRA05Y.cpy 5. PIC X(16).
        object.__setattr__(self, "tran_id", require_text(self.tran_id, _width(pictures, "TRAN-ID"), "TRAN-ID"))
        # CVTRA05Y.cpy 6. PIC X(02).
        object.__setattr__(
            self,
            "tran_type_cd",
            require_text(self.tran_type_cd, _width(pictures, "TRAN-TYPE-CD"), "TRAN-TYPE-CD"),
        )
        # CVTRA05Y.cpy 7. PIC 9(04). MOVE '05' stores as 0005. CBACT04C.cbl 483.
        object.__setattr__(
            self,
            "tran_cat_cd",
            require_digits(self.tran_cat_cd, _width(pictures, "TRAN-CAT-CD"), "TRAN-CAT-CD"),
        )
        # CVTRA05Y.cpy 8. PIC X(10).
        object.__setattr__(
            self,
            "tran_source",
            require_text(self.tran_source, _width(pictures, "TRAN-SOURCE"), "TRAN-SOURCE"),
        )
        # CVTRA05Y.cpy 9. PIC X(100). STRING does not space-fill by itself;
        # the picture does. CBACT04C.cbl 485-489.
        object.__setattr__(
            self,
            "tran_desc",
            require_text(self.tran_desc, _width(pictures, "TRAN-DESC"), "TRAN-DESC"),
        )
        # CVTRA05Y.cpy 10. PIC S9(09)V99. CBACT04C.cbl 490.
        object.__setattr__(self, "tran_amt", S9_09_V99.store(self.tran_amt))
        # CVTRA05Y.cpy 11. PIC 9(09).
        object.__setattr__(
            self,
            "tran_merchant_id",
            require_digits(self.tran_merchant_id, _width(pictures, "TRAN-MERCHANT-ID"), "TRAN-MERCHANT-ID"),
        )
        # CVTRA05Y.cpy 12. PIC X(50).
        object.__setattr__(
            self,
            "tran_merchant_name",
            require_text(self.tran_merchant_name, _width(pictures, "TRAN-MERCHANT-NAME"), "TRAN-MERCHANT-NAME"),
        )
        # CVTRA05Y.cpy 13. PIC X(50).
        object.__setattr__(
            self,
            "tran_merchant_city",
            require_text(self.tran_merchant_city, _width(pictures, "TRAN-MERCHANT-CITY"), "TRAN-MERCHANT-CITY"),
        )
        # CVTRA05Y.cpy 14. PIC X(10).
        object.__setattr__(
            self,
            "tran_merchant_zip",
            require_text(self.tran_merchant_zip, _width(pictures, "TRAN-MERCHANT-ZIP"), "TRAN-MERCHANT-ZIP"),
        )
        # CVTRA05Y.cpy 15. PIC X(16).
        object.__setattr__(
            self,
            "tran_card_num",
            require_text(self.tran_card_num, _width(pictures, "TRAN-CARD-NUM"), "TRAN-CARD-NUM"),
        )
        # CVTRA05Y.cpy 16-17. PIC X(26). Layout YYYY-MM-DD-HH.MM.SS.nn0000 is CBACT04C.cbl 613-624.
        object.__setattr__(
            self,
            "tran_orig_ts",
            require_text(self.tran_orig_ts, _width(pictures, "TRAN-ORIG-TS"), "TRAN-ORIG-TS"),
        )
        object.__setattr__(
            self,
            "tran_proc_ts",
            require_text(self.tran_proc_ts, _width(pictures, "TRAN-PROC-TS"), "TRAN-PROC-TS"),
        )


def picture_total(pictures: Sequence[Picture]) -> int:
    return sum(width for _, width in pictures)
