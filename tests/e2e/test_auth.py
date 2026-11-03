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
"""End-to-end tests for the app tokens MSS accepts and refuses"""
import os

import pytest
from qiskit import QuantumCircuit, transpile

from tergite import Tergite

# app tokens in tergite-frontend's ui/fixtures/tokens.json, with which MSS is seeded
REFUSED_TOKENS = {
    "unknown": "not-a-token-mss-has",
    "expired": "7e80d9eead6f36497f5563864a6cdc7934566903ace26e3f",
    "inactive project": "c90f2b3ee9b161cdafc63d3f15f2c2cf79a8c6cf19e3519f",
    "no QPU seconds left": "3f18253685955b7b67324f19dd0d506936bee1de8b422031",
}


@pytest.mark.parametrize("token", REFUSED_TOKENS.values(), ids=REFUSED_TOKENS.keys())
def test_refused_token_cannot_submit(token: str):
    """MSS refuses a job submitted with an unknown or expired token, or that of an inactive
    project or of one with no QPU seconds left"""
    provider = Tergite.use_provider_account(
        service_name="refused", url=os.environ["API_URL"], token=token
    )
    backend = provider.get_backend("qiskit_pulse_1q")
    qc = QuantumCircuit(1, 1)
    qc.measure(0, 0)

    with pytest.raises(RuntimeError, match="unable to register job"):
        backend.run(transpile(qc, backend=backend))
