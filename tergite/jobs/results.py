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
"""The qiskit Result of a job, from the memory the backend returned"""
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from qiskit import QuantumCircuit
from qiskit.result import Result
from qiskit.result.models import ExperimentResult, ExperimentResultData

from ..exc import ApiError


@dataclass(frozen=True)
class CircuitHeader:
    """What the result of a circuit needs of it: its name and its classical registers"""

    name: str
    creg_sizes: List[List[Any]]
    memory_slots: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_circuit(cls, circuit: QuantumCircuit) -> "CircuitHeader":
        """Gets the header of the circuit

        Args:
            circuit: the circuit

        Returns:
            its name, the name and size of each classical register, and its metadata
        """
        return cls(
            name=circuit.name,
            creg_sizes=[[creg.name, creg.size] for creg in circuit.cregs],
            memory_slots=circuit.num_clbits,
            metadata=dict(circuit.metadata or {}),
        )


def get_result(
    *,
    job_id: str,
    backend_name: str,
    backend_version: str,
    headers: Optional[Sequence[CircuitHeader]],
    shots: int,
    meas_level: int,
    meas_return: str,
    memory: List[Any],
) -> Result:
    """Gets the result of a successful job from the memory the backend returned

    Args:
        job_id: the id of the job
        backend_name: the name of the backend that ran it
        backend_version: the version of that backend
        headers: the header of each circuit of the job, or None where they are unknown,
            as for a job got by its id
        shots: the shots of each circuit
        meas_level: 2 for counts, 1 for IQ points, 0 for traces
        meas_return: single for each shot's, avg for their average
        memory: per circuit, at meas_level 2 each shot's bits as hex, in clbit order;
            else each shot's IQ point per measured clbit, one shot for avg

    Returns:
        the result

    Raises:
        ApiError: unexpected number of results; expected {n}, got: {m}
    """
    if headers is not None and len(memory) != len(headers):
        raise ApiError(
            f"unexpected number of results; expected {len(headers)}, got: {len(memory)}"
        )

    has_counts = meas_level == 2
    # the backend sends an average as one shot, where Qiskit reads a point per slot
    is_averaged = not has_counts and meas_return == "avg"
    return Result(
        backend_name=backend_name,
        backend_version=backend_version,
        job_id=job_id,
        success=True,
        results=[
            ExperimentResult(
                shots=shots,
                success=True,
                meas_level=meas_level,
                meas_return=meas_return,
                header=None if headers is None else asdict(headers[index]),
                data=ExperimentResultData(
                    counts=dict(Counter(values)) if has_counts else None,
                    memory=values[0] if is_averaged else values,
                ),
            )
            for index, values in enumerate(memory)
        ],
    )
