"""ASCII trailing overpunch for the interest-batch money pictures."""

import unittest
from decimal import Decimal

from intcalc.zoned import ZonedDecimalError, decode_zoned, encode_zoned


class ZonedDecimalTests(unittest.TestCase):
    def test_overpunch_round_trips_with_implied_decimals(self) -> None:
        # CVTRA02Y.cpy line 9: S9(04)V99 is 6 bytes. 00150{ is +15.00, not 150.
        self.assertEqual(decode_zoned("00150{", 2), Decimal("15.00"))
        self.assertEqual(encode_zoned(Decimal("15.00"), 6, 2), "00150{")
        # CVTRA05Y.cpy line 10: S9(09)V99 is 11 bytes. G is the positive 7.
        self.assertEqual(decode_zoned("0000005047G", 2), Decimal("504.77"))
        self.assertEqual(encode_zoned(Decimal("504.77"), 11, 2), "0000005047G")

    def test_every_trailing_overpunch_digit_round_trips(self) -> None:
        positive = "{ABCDEFGHI"
        negative = "}JKLMNOPQR"
        for digit, (pos, neg) in enumerate(zip(positive, negative)):
            # The overpunch is the last digit, not an extra character.
            # "00010" + digit, scale 2, is 1.00 through 1.09.
            raw_pos = "00010" + pos
            raw_neg = "00010" + neg
            amount = (Decimal(100) + Decimal(digit)) / Decimal(100)
            self.assertEqual(decode_zoned(raw_pos, 2), amount)
            self.assertEqual(encode_zoned(decode_zoned(raw_pos, 2), 6, 2), raw_pos)
            self.assertEqual(decode_zoned(raw_neg, 2), -amount)
            self.assertEqual(encode_zoned(decode_zoned(raw_neg, 2), 6, 2), raw_neg)

    def test_negative_zero_stays_negative_zero(self) -> None:
        # "}" is negative 0. Re-encoding must not flip it to "{".
        raw = "00000}"
        decoded = decode_zoned(raw, 2)
        self.assertEqual(decoded, Decimal("0.00"))
        self.assertTrue(decoded.is_signed())
        self.assertEqual(encode_zoned(decoded, 6, 2), raw)

    def test_truncates_toward_zero_when_the_picture_is_not_rounded(self) -> None:
        # No ROUNDED on S9(09)V99. CVTRA01Y.cpy line 9. -1.239 -> -1.23, not -1.24.
        self.assertEqual(encode_zoned(Decimal("1.239"), 11, 2), "0000000012C")
        self.assertEqual(encode_zoned(Decimal("-1.239"), 11, 2), "0000000012L")
        self.assertEqual(decode_zoned("0000000012L", 2), Decimal("-1.23"))

    def test_rejects_a_value_that_does_not_fit(self) -> None:
        # S9(04)V99 holds at most 9999.99. CVTRA02Y.cpy line 9.
        with self.assertRaises(ZonedDecimalError):
            encode_zoned(Decimal("10000.00"), 6, 2)

    def test_rejects_non_numeric_and_float(self) -> None:
        with self.assertRaises(ZonedDecimalError):
            decode_zoned("0015A ", 2)
        with self.assertRaises(ZonedDecimalError):
            decode_zoned("0015AX", 2)
        with self.assertRaises(TypeError):
            encode_zoned(1.5, 6, 2)
        with self.assertRaises(TypeError):
            encode_zoned(True, 6, 2)


if __name__ == "__main__":
    unittest.main()
