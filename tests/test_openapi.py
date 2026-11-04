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
"""Tests that the SDK's wire models are what the services' specs generate"""

import pytest

from dev.openapi.generate import CONTRACTS, Contract, render_models


@pytest.mark.parametrize("contract", CONTRACTS, ids=lambda c: c.spec_file.name)
def test_models_match_their_spec(contract: Contract):
    """A changed spec, or a hand-edited model, fails until the models are regenerated"""
    assert contract.models_file.read_text() == render_models(contract), (
        f"{contract.models_file.name} is stale: run python -m dev.openapi.generate"
    )
