"""Copybook layouts used by CBACT04C. Lengths include FILLER."""

import unittest
from dataclasses import fields
from decimal import Decimal

from interest.records import (
    AccountRecord,
    CardXrefRecord,
    DisGroupRecord,
    TranCatBalRecord,
    TranRecord,
    picture_total,
)

_PAN = "0000000000004242"
_ACCOUNT = "12345678901"


def _account(**overrides: object) -> AccountRecord:
    values = {
        "acct_id": _ACCOUNT,
        "acct_active_status": "Y",
        "acct_curr_bal": Decimal("10.239"),
        "acct_credit_limit": Decimal("5000"),
        "acct_cash_credit_limit": Decimal("1000"),
        "acct_open_date": "2020-01-01",
        "acct_expiration_date": "2028-01-01",
        "acct_reissue_date": "2024-01-01",
        "acct_curr_cyc_credit": Decimal("1.009"),
        "acct_curr_cyc_debit": Decimal("2"),
        "acct_addr_zip": "46204",
        "acct_group_id": "DEFAULT",
    }
    values.update(overrides)
    return AccountRecord(**values)  # type: ignore[arg-type]


def _transaction(**overrides: object) -> TranRecord:
    values = {
        "tran_id": "2022071800000001",
        "tran_type_cd": "01",
        "tran_cat_cd": "05",
        "tran_source": "System",
        "tran_desc": "Int. for a/c " + _ACCOUNT,
        "tran_amt": Decimal("1.239"),
        "tran_merchant_id": 0,
        "tran_merchant_name": "",
        "tran_merchant_city": "",
        "tran_merchant_zip": "",
        "tran_card_num": _PAN,
        "tran_orig_ts": "2022-07-18-00.00.00.000000",
        "tran_proc_ts": "2022-07-18-00.00.00.000000",
    }
    values.update(overrides)
    return TranRecord(**values)  # type: ignore[arg-type]


class RecordLayoutTests(unittest.TestCase):
    def test_picture_widths_match_copybook_record_lengths(self) -> None:
        # CVTRA01Y.cpy 2, CVTRA02Y.cpy 2, CVACT03Y.cpy 2: RECLN 50.
        # CVACT01Y.cpy 2: RECLN 300. CVTRA05Y.cpy 2: RECLN 350.
        expected = {
            TranCatBalRecord: 50,
            DisGroupRecord: 50,
            AccountRecord: 300,
            CardXrefRecord: 50,
            TranRecord: 350,
        }
        for record_type, length in expected.items():
            self.assertEqual(picture_total(record_type.PICTURES), length)
            self.assertEqual(record_type.RECORD_LENGTH, length)
            named = [name for name, _ in record_type.PICTURES if name != "FILLER"]
            self.assertEqual(len(named), len(fields(record_type)))

    def test_category_balance_picture(self) -> None:
        # CVTRA01Y.cpy 6-9. PIC 9(11), X(02), 9(04), S9(09)V99.
        record = TranCatBalRecord("1", "1", "5", Decimal("-10.239"))
        self.assertEqual(record.trancat_acct_id, "00000000001")
        self.assertEqual(record.trancat_type_cd, "1 ")
        self.assertEqual(record.trancat_cd, "0005")
        self.assertEqual(record.tran_cat_bal, Decimal("-10.23"))
        self.assertNotIn(record.trancat_acct_id, repr(record))

    def test_category_balance_rejects_float(self) -> None:
        with self.assertRaises(TypeError):
            TranCatBalRecord("1", "01", "0001", 1.5)

    def test_disclosure_group_pads_default_and_truncates_rate(self) -> None:
        # DIS-ACCT-GROUP-ID PIC X(10), DIS-INT-RATE PIC S9(04)V99. CVTRA02Y.cpy 6, 9.
        record = DisGroupRecord("DEFAULT", "01", "5", "12.345")
        self.assertEqual(record.dis_acct_group_id, "DEFAULT   ")
        self.assertEqual(len(record.dis_acct_group_id), 10)
        self.assertEqual(record.dis_int_rate, Decimal("12.34"))

    def test_account_money_and_group(self) -> None:
        # CVACT01Y.cpy 7, 13-16. Balances S9(10)V99. Group id PIC X(10).
        record = _account()
        self.assertEqual(record.acct_id, _ACCOUNT)
        self.assertEqual(record.acct_curr_bal, Decimal("10.23"))
        self.assertEqual(record.acct_curr_cyc_credit, Decimal("1.00"))
        self.assertEqual(record.acct_curr_cyc_debit, Decimal("2.00"))
        self.assertEqual(record.acct_group_id, "DEFAULT   ")
        self.assertEqual(len(record.acct_open_date), 10)
        shown = repr(record)
        self.assertNotIn(_ACCOUNT, shown)
        self.assertNotIn("46204", shown)
        self.assertNotIn("2020-01-01", shown)
        self.assertIn("8901", shown)

    def test_xref_card_and_account(self) -> None:
        # CVACT03Y.cpy 5-7. Card PIC X(16), customer PIC 9(09), account PIC 9(11).
        record = CardXrefRecord(_PAN, "123456789", "1")
        self.assertEqual(record.xref_card_num, _PAN)
        self.assertEqual(len(record.xref_card_num), 16)
        self.assertEqual(record.xref_cust_id, "123456789")
        self.assertEqual(record.xref_acct_id, "00000000001")
        shown = repr(record)
        self.assertNotIn(_PAN, shown)
        self.assertNotIn("123456789", shown)
        self.assertIn("4242", shown)

    def test_overlong_card_is_rejected_without_echoing_it(self) -> None:
        pan = _PAN + "9999"
        with self.assertRaises(ValueError) as raised:
            CardXrefRecord(pan, "1", "1")
        self.assertNotIn(pan, str(raised.exception))

    def test_transaction_length_and_amount(self) -> None:
        # CVTRA05Y.cpy 5-17. TRAN-AMT PIC S9(09)V99. Timestamps PIC X(26).
        # MOVE '05' to PIC 9(04) is 0005. CBACT04C.cbl 483.
        record = _transaction()
        self.assertEqual(record.tran_cat_cd, "0005")
        self.assertEqual(record.tran_amt, Decimal("1.23"))
        self.assertEqual(len(record.tran_desc), 100)
        self.assertTrue(record.tran_desc.startswith("Int. for a/c " + _ACCOUNT))
        self.assertEqual(len(record.tran_orig_ts), 26)
        self.assertEqual(len(record.tran_proc_ts), 26)
        self.assertEqual(record.tran_merchant_id, "000000000")
        shown = repr(record)
        self.assertNotIn(_PAN, shown)
        self.assertNotIn(_ACCOUNT, shown)
        self.assertIn("4242", shown)


if __name__ == "__main__":
    unittest.main()
