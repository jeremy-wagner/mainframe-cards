"""Cent truncation for CBACT04C pictures that are not ROUNDED."""

import unittest
from decimal import Decimal

from interest.money import S9_04_V99, S9_09_V99, S9_10_V99, store_money


class StoreMoneyTests(unittest.TestCase):
    def test_rejects_float(self) -> None:
        # CBACT04C.cbl 168. Money is decimal, never float.
        with self.assertRaises(TypeError):
            store_money(1.239, integer_digits=9, scale=2)

    def test_rejects_bool(self) -> None:
        with self.assertRaises(TypeError):
            store_money(True, integer_digits=9, scale=2)

    def test_truncates_positive_toward_zero(self) -> None:
        # COMPUTE has no ROUNDED. CBACT04C.cbl 464-465. 1.239 -> 1.23, not 1.24.
        stored = store_money(Decimal("1.239"), integer_digits=9, scale=2)
        self.assertEqual(stored, Decimal("1.23"))
        self.assertIsInstance(stored, Decimal)
        self.assertEqual(stored.as_tuple().exponent, -2)

    def test_truncates_negative_toward_zero(self) -> None:
        # ROUND_DOWN, not ROUND_FLOOR: -1.239 -> -1.23. CBACT04C.cbl 168.
        stored = store_money(Decimal("-1.239"), integer_digits=9, scale=2)
        self.assertEqual(stored, Decimal("-1.23"))

    def test_rate_picture_does_not_round_up(self) -> None:
        # DIS-INT-RATE PIC S9(04)V99. CVTRA02Y.cpy 9.
        self.assertEqual(S9_04_V99.store("18.999"), Decimal("18.99"))
        self.assertEqual(S9_04_V99.width, 6)

    def test_category_balance_rejects_tenth_integer_digit(self) -> None:
        # TRAN-CAT-BAL PIC S9(09)V99. CVTRA01Y.cpy 9.
        with self.assertRaises(ValueError):
            S9_09_V99.store(Decimal("1000000000.00"))
        self.assertEqual(S9_09_V99.store(Decimal("999999999.999")), Decimal("999999999.99"))

    def test_account_balance_holds_one_more_integer_digit(self) -> None:
        # ACCT-CURR-BAL PIC S9(10)V99. CVACT01Y.cpy 7.
        stored = S9_10_V99.store(Decimal("1000000000.009"))
        self.assertEqual(stored, Decimal("1000000000.00"))
        self.assertEqual(S9_10_V99.width, 12)

    def test_rejects_non_finite(self) -> None:
        with self.assertRaises(ValueError):
            store_money("NaN", integer_digits=9, scale=2)


if __name__ == "__main__":
    unittest.main()
