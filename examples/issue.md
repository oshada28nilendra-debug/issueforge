# Currency totals contain floating point noise

Calling prices.total(['0.10', '0.20']) should return Decimal('0.30') exactly.
Instead the buggy version includes extra decimal digits. Whole amounts still pass.
Please produce a small regression test demonstrating the exact expected behavior.
