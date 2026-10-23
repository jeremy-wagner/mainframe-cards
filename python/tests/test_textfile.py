"""Byte-for-byte round trip of the ASCII interest-batch exports."""

import unittest
from decimal import Decimal
from pathlib import Path

from intcalc.records import (
    AccountRecord,
    CardXrefRecord,
    DisGroupRecord,
    RecordFormatError,
    TranCatBalRecord,
    TranRecord,
)
from intcalc.textfile import read_records, reserialize

_ASCII = Path(__file__).resolve().parents[2] / "app" / "data" / "ASCII"


def _same_bytes(testcase: unittest.TestCase, actual: bytes, expected: bytes) -> None:
    if actual == expected:
        return
    limit = min(len(actual), len(expected))
    offset = next((index for index in range(limit) if actual[index] != expected[index]), limit)
    testcase.fail(
        f"byte mismatch at offset {offset} "
        f"(lengths {len(actual)} and {len(expected)})"
    )


class TextFileTests(unittest.TestCase):
    def test_category_disclosure_account_and_xref_round_trip(self) -> None:
        files = {
            "tcatbal.txt": TranCatBalRecord,
            "discgrp.txt": DisGroupRecord,
            "acctdata.txt": AccountRecord,
            "cardxref.txt": CardXrefRecord,
        }
        for name, record_type in files.items():
            original = (_ASCII / name).read_bytes()
            with self.subTest(name=name):
                _same_bytes(self, reserialize(original, record_type), original)

    def test_exported_values_keep_scale_and_filler(self) -> None:
        category = read_records((_ASCII / "tcatbal.txt").read_bytes(), TranCatBalRecord)
        # CVTRA01Y.cpy line 9. Sample balance is positive zero, filler is zeros.
        self.assertEqual(category[0].tran_cat_bal, Decimal("0.00"))
        self.assertFalse(category[0].tran_cat_bal.is_signed())
        self.assertEqual(category[0].filler, "0" * 22)
        self.assertEqual(len(category[0].to_bytes()), 50)

        disclosure = read_records((_ASCII / "discgrp.txt").read_bytes(), DisGroupRecord)
        # CVTRA02Y.cpy line 9. 00150{ is 15.00 percent. DEFAULT is space padded.
        self.assertEqual(disclosure[0].dis_int_rate, Decimal("15.00"))
        default = next(row for row in disclosure if row.dis_acct_group_id.startswith("DEFAULT"))
        self.assertEqual(default.dis_acct_group_id, "DEFAULT   ")
        self.assertEqual(default.dis_int_rate, Decimal("15.00"))

        account = read_records((_ASCII / "acctdata.txt").read_bytes(), AccountRecord)
        # CVACT01Y.cpy lines 7-16. 00000001940{ is 194.00, not 1940.00.
        self.assertEqual(account[0].acct_active_status, "Y")
        self.assertEqual(account[0].acct_curr_bal, Decimal("194.00"))
        self.assertEqual(account[0].acct_credit_limit, Decimal("2020.00"))
        self.assertEqual(account[0].acct_cash_credit_limit, Decimal("1020.00"))
        self.assertEqual(account[0].acct_open_date, "2014-11-20")
        self.assertEqual(account[0].acct_curr_cyc_credit, Decimal("0.00"))
        self.assertEqual(account[0].acct_curr_cyc_debit, Decimal("0.00"))
        self.assertEqual(account[0].acct_addr_zip, "A000000000")
        self.assertEqual(account[0].acct_group_id, " " * 10)
        self.assertEqual(len(account[0].to_bytes()), 300)

        xref = read_records((_ASCII / "cardxref.txt").read_bytes(), CardXrefRecord)
        # CVACT03Y.cpy lines 5-8. The export omits the 14 space filler.
        self.assertEqual(len(xref), 50)
        self.assertEqual(len(xref[0].xref_card_num), 16)
        self.assertEqual(len(xref[0].xref_cust_id), 9)
        self.assertEqual(len(xref[0].xref_acct_id), 11)
        self.assertEqual(xref[0].filler, " " * 14)
        self.assertEqual(len(xref[0].to_bytes()), 50)

    def test_transaction_export_round_trips(self) -> None:
        # CVTRA05Y.cpy lines 4-18. Not required by the file list, but the same codec.
        original = (_ASCII / "dailytran.txt").read_bytes()
        _same_bytes(self, reserialize(original, TranRecord), original)
        first = read_records(original, TranRecord)[0]
        self.assertEqual(first.tran_amt, Decimal("504.77"))
        self.assertEqual(len(first.to_bytes()), 350)

    def test_short_xref_line_is_not_a_50_byte_buffer(self) -> None:
        line = (_ASCII / "cardxref.txt").read_bytes().splitlines()[0]
        self.assertEqual(len(line), 36)
        with self.assertRaises(RecordFormatError) as raised:
            CardXrefRecord.from_bytes(line)
        self.assertIn("50 bytes", str(raised.exception))
        self.assertNotIn(line.decode("ascii"), str(raised.exception))

    def test_overlong_line_names_the_length_only(self) -> None:
        payload = b"9" * 51 + b"\n"
        with self.assertRaises(RecordFormatError) as raised:
            read_records(payload, TranCatBalRecord)
        message = str(raised.exception)
        self.assertIn("got 51", message)
        self.assertNotIn("999", message)


if __name__ == "__main__":
    unittest.main()
