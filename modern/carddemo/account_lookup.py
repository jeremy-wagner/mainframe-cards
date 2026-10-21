"""Account lookup by ID, ported from COACTVWC.cbl (2210-EDIT-ACCOUNT, 9300-GETACCTDATA-BYACCT).

Record layout follows app/cpy/CVACT01Y.cpy (ACCOUNT-RECORD).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

# CVACT01Y.cpy line 5: ACCT-ID PIC 9(11)
ACCT_ID_LENGTH = 11

_SELECT_ACCOUNT = """
    SELECT acct_id, active_status, curr_bal, credit_limit, cash_credit_limit,
           open_date, expiration_date, reissue_date, curr_cyc_credit,
           curr_cyc_debit, addr_zip, group_id
      FROM account
     WHERE acct_id = ?
"""


class AccountLookupError(Exception):
    pass


class InvalidAccountIdError(AccountLookupError):
    pass


class AccountNotFoundError(AccountLookupError):
    pass


class AccountAccessDeniedError(AccountLookupError):
    pass


@dataclass(frozen=True)
class Account:
    acct_id: int
    active_status: str
    curr_bal: Decimal
    credit_limit: Decimal
    cash_credit_limit: Decimal
    open_date: str
    expiration_date: str
    reissue_date: str
    curr_cyc_credit: Decimal
    curr_cyc_debit: Decimal
    addr_zip: str
    group_id: str


def mask_account_id(acct_id: str | int) -> str:
    text = str(acct_id)
    return "*" * max(len(text) - 4, 0) + text[-4:]


def validate_account_id(raw: str | None) -> int:
    # COACTVWC.cbl lines 653-661: blank or LOW-VALUES means not supplied.
    if raw is None or raw.strip() == "":
        raise InvalidAccountIdError("Account number not provided")

    # COACTVWC.cbl lines 666-673: must be a non-zero 11 digit number.
    # isascii() keeps non-ASCII Unicode digits out, matching COBOL's NUMERIC class test.
    if not (len(raw) == ACCT_ID_LENGTH and raw.isascii() and raw.isdigit()) or int(raw) == 0:
        raise InvalidAccountIdError("Account Filter must be a non-zero 11 digit number")

    return int(raw)


def _to_decimal(value: object) -> Decimal:
    # Money columns are S9(10)V99 (CVACT01Y.cpy lines 7-9, 13-14); go through str so
    # a REAL-typed column never reaches Decimal as a binary float.
    return Decimal(str(value))


def get_account(
    conn: sqlite3.Connection,
    raw_acct_id: str | None,
    user_id: str,
    can_access_account: Callable[[str, int], bool],
) -> Account:
    acct_id = validate_account_id(raw_acct_id)

    if not can_access_account(user_id, acct_id):
        raise AccountAccessDeniedError(
            f"Access denied for account {mask_account_id(raw_acct_id)}"
        )

    row = conn.execute(_SELECT_ACCOUNT, (acct_id,)).fetchone()

    # COACTVWC.cbl lines 788-806: NOTFND on the account master.
    if row is None:
        raise AccountNotFoundError(
            f"Account {mask_account_id(raw_acct_id)} not found in Acct Master file"
        )

    return Account(
        acct_id=row[0],
        active_status=row[1],
        curr_bal=_to_decimal(row[2]),
        credit_limit=_to_decimal(row[3]),
        cash_credit_limit=_to_decimal(row[4]),
        open_date=row[5],
        expiration_date=row[6],
        reissue_date=row[7],
        curr_cyc_credit=_to_decimal(row[8]),
        curr_cyc_debit=_to_decimal(row[9]),
        addr_zip=row[10],
        group_id=row[11],
    )
