# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2025
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""The job file uploaded to the backend, whose schema the backend's spec does not hold

Its shape follows qpi's JobPayload, so that the two stacks read alike.
"""
from typing import Any, Dict, List

from pydantic import BaseModel


class CircuitPayload(BaseModel):
    """A circuit of the job, in OpenQASM 3"""

    name: str
    qasm: str
    num_clbits: int
    metadata: Dict[str, Any] = {}


class JobParams(BaseModel):
    """The circuits of the job, and how to run and measure them"""

    circuits: List[CircuitPayload]
    shots: int
    meas_level: int
    meas_return: str


class JobFile(BaseModel):
    """The job file the backend runs"""

    job_id: str
    params: JobParams
