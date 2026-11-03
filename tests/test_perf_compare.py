# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""Tests for dev/perf/compare.py, which decides whether a refactor step made the SDK slower"""
import pytest

from dev.perf.compare import Measure, is_worse_than_allowed


@pytest.mark.parametrize(
    "unit, before, after, expected",
    [
        ("ms", 100.0, 109.0, False),
        ("ms", 100.0, 120.0, True),
        ("ms", 10.0, 14.0, False),
        ("roundtrip_ms", 500.0, 590.0, False),
        ("roundtrip_ms", 2000.0, 2300.0, True),
        ("jobs/min", 30.0, 20.0, True),
        ("jobs/min", 30.0, 40.0, False),
        ("calls", 2.0, 3.0, True),
        ("calls", 3.0, 2.0, False),
        ("MiB", 100.0, 104.0, False),
    ],
)
def test_worse_than_allowed(unit: str, before: float, after: float, expected: bool):
    """Worse by more than 10% and the noise floor, or one HTTP call more, is a regression"""
    got = is_worse_than_allowed(Measure("m", unit, before), Measure("m", unit, after))

    assert got == expected
