import unittest
from decimal import Decimal
from prices import total


class TestSmoke(unittest.TestCase):
    def test_whole_amounts(self):
        self.assertEqual(total(["1", "2"]), Decimal("3"))
