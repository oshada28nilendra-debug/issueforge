"""Supplied fixture: this test was authored by a human/assistant, not a live model."""

import unittest
from decimal import Decimal
from prices import total


class TestCurrencyRegression(unittest.TestCase):
    def test_tenths_are_exact(self):
        self.assertEqual(total(["0.10", "0.20"]), Decimal("0.30"))
