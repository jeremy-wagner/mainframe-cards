"""Copybook lengths, picture scale, and boundary rejection."""

import unittest
from decimal import Decimal

from intcalc.records import (
    AccountRecord,
    CardXrefRecord,
    DisGroupRecord,
    RecordFormatError,
    TranCatBalRecord,
    TranRecord,
)


_PAN = "4111111111111111"
_ACCOUNT = "12345678901"


class RecordLayoutTests(unittest.TestCase):
    def test_picture_widths_match_the_copybook_lengths(self) -> None:
        # CVTRA01Y.cpy line 2, CVACT03Y.cpy line 2, CVTRA02Y.cpy line 2: 50.
        # CVACT01Y.cpy line 2: 300. CVTRA05Y.cpy line 2: 350.
        expected = {
            TranCatBalRecord: 50,
            CardXrefRecord: 50,
            DisGroupRecord: 50,
            AccountRecord: 300,
            TranRecord: 350,
        }
        for record_type, length in expected.items():
            total = sum(field.width for field in record_type.LAYOUT)
            self.assertEqual(total, length)
            self.assertEqual(record_type.RECORD_LENGTH, length)

    def test_category_balance_is_signed_with_two_decimals(self) -> None:
        # CVTRA01Y.cpy lines 6-10. S9(09)V99 truncates, it does not round.
        record = TranCatBalRecord("1", "01", "5", Decimal("-10.239"))
        self.assertEqual(record.trancat_acct_id, "00000000001")
        self.assertEqual(record.trancat_cd, "0005")
        self.assertEqual(record.tran_cat_bal, Decimal("-10.23"))
        encoded = record.to_bytes()
        self.assertEqual(len(encoded), 50)
        # -10.23 is digits 00000001023. L is the negative overpunch for 3.
        self.assertEqual(encoded[17:28], b"0000000102L")
        self.assertEqual(TranCatBalRecord.from_bytes(encoded), record)

    def test_disclosure_rate_picture(self) -> None:
        # CVTRA02Y.cpy lines 6 and 9. DEFAULT is 7 characters in PIC X(10).
        record = DisGroupRecord("DEFAULT", "01", "1", Decimal("12.349"))
        self.assertEqual(record.dis_acct_group_id, "DEFAULT   ")
        self.assertEqual(record.dis_int_rate, Decimal("12.34"))
        encoded = record.to_bytes()
        self.assertEqual(len(encoded), 50)
        self.assertEqual(encoded[16:22], b"00123D")

    def test_account_balance_and_cycle_pictures(self) -> None:
        # CVACT01Y.cpy lines 7-9 and 13-14. S9(10)V99 is 12 bytes.
        record = AccountRecord(
            acct_id=_ACCOUNT,
            acct_active_status="Y",
            acct_curr_bal=Decimal("1940.009"),
            acct_credit_limit=Decimal("2020"),
            acct_cash_credit_limit=Decimal("1020"),
            acct_open_date="2014-11-20",
            acct_expiration_date="2025-05-20",
            acct_reissue_date="2025-05-20",
            acct_curr_cyc_credit=Decimal("0"),
            acct_curr_cyc_debit=Decimal("-1.239"),
            acct_addr_zip="46204",
            acct_group_id="DEFAULT",
        )
        self.assertEqual(record.acct_curr_bal, Decimal("1940.00"))
        self.assertEqual(record.acct_curr_cyc_debit, Decimal("-1.23"))
        self.assertEqual(record.acct_group_id, "DEFAULT   ")
        encoded = record.to_bytes()
        self.assertEqual(len(encoded), 300)
        self.assertEqual(encoded[12:24], b"00000019400{")
        self.assertEqual(AccountRecord.from_bytes(encoded).acct_curr_bal, Decimal("1940.00"))

    def test_cross_reference_is_50_bytes(self) -> None:
        # CVACT03Y.cpy lines 5-8.
        record = CardXrefRecord(_PAN, "123456789", "1")
        encoded = record.to_bytes()
        self.assertEqual(len(encoded), 50)
        self.assertEqual(encoded[36:], b" " * 14)
        self.assertEqual(CardXrefRecord.from_bytes(encoded).xref_acct_id, "00000000001")

    def test_transaction_record_is_350_bytes(self) -> None:
        # CVTRA05Y.cpy lines 5-18. TRAN-AMT is S9(09)V99.
        record = TranRecord(
            tran_id="2022071800000001",
            tran_type_cd="01",
            tran_cat_cd="5",
            tran_source="System",
            tran_desc="Int. for a/c " + _ACCOUNT,
            tran_amt=Decimal("1.239"),
            tran_merchant_id=0,
            tran_merchant_name="",
            tran_merchant_city="",
            tran_merchant_zip="",
            tran_card_num=_PAN,
            tran_orig_ts="2022-07-18-00.00.00.000000",
            tran_proc_ts="2022-07-18-00.00.00.000000",
        )
        self.assertEqual(record.tran_cat_cd, "0005")
        self.assertEqual(record.tran_amt, Decimal("1.23"))
        encoded = record.to_bytes()
        self.assertEqual(len(encoded), 350)
        self.assertEqual(encoded[132:143], b"0000000012C")
        self.assertEqual(TranRecord.from_bytes(encoded).tran_amt, Decimal("1.23"))

    def test_wrong_length_is_rejected_without_echoing_the_card(self) -> None:
        data = (_PAN + ("0" * 40)).encode("ascii")
        with self.assertRaises(RecordFormatError) as raised:
            CardXrefRecord.from_bytes(data)
        message = str(raised.exception)
        self.assertIn("50 bytes", message)
        self.assertNotIn(_PAN, message)

    def test_non_numeric_field_is_rejected_without_echoing_the_account(self) -> None:
        # 11-byte account id is not numeric. The rest of the 50-byte record is spaces.
        raw = b"ABCDEFGHIJK" + (b" " * 39)
        with self.assertRaises(RecordFormatError) as raised:
            TranCatBalRecord.from_bytes(raw)
        message = str(raised.exception)
        self.assertIn("not numeric", message)
        self.assertNotIn("ABCDEFGHIJK", message)

    def test_repr_masks_card_and_account(self) -> None:
        record = CardXrefRecord(_PAN, "123456789", _ACCOUNT)
        shown = repr(record)
        self.assertNotIn(_PAN, shown)
        self.assertNotIn("123456789", shown)
        self.assertNotIn(_ACCOUNT, shown)
        self.assertIn("1111", shown)
        self.assertIn("8901", shown)

    def test_float_money_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            TranCatBalRecord("1", "01", "0001", 1.5)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
