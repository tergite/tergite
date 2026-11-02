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
"""The results users get for the ways a circuit can measure into its classical bits.

The backend returns each shot's bits in the circuit's clbit order, clbit 0 rightmost. These
cases pin what the user then reads from job.result(), so that the gate-level payload of
REFACTOR.md's step 4 can be shown to answer exactly as the pulse payload does.
"""
from typing import Any, Dict, List

import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile

from tergite import Tergite
from tests.utils.qobj_tools import extract_uploaded_qobj_from_request

from .conftest import API_URL, TEST_CALIBRATIONS_MAP, TEST_JOB_ID

BACKEND_NAME = "qiskit_pulse_2q"
_IQ_SHOTS = [[[0.5, -0.25], [1.5, 2.0]], [[-1.0, 0.75], [0.0, 0.125]]]


def test_bell_pair_into_c(api):
    """Counts of a Bell pair measured into the circuit's own register"""
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])

    result = _run_with_memory(api, [qc], memory=[["0x0", "0x3", "0x3"]])

    assert result.get_counts() == {"00": 1, "11": 2}


def test_measure_all(api):
    """Counts of measure_all(), whose bits go to its own 'meas' register"""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    result = _run_with_memory(api, [qc], memory=[["0x0", "0x3", "0x3"]])

    assert result.get_counts() == {"00": 1, "11": 2}


def test_partial_measurement(api):
    """Counts of a circuit that measures one of its two qubits into its one clbit"""
    qc = QuantumCircuit(2, 1)
    qc.x(1)
    qc.measure(1, 0)

    result = _run_with_memory(api, [qc], memory=[["0x1", "0x1", "0x0"]])

    assert result.get_counts() == {"1": 2, "0": 1}
    assert _get_uploaded_q_to_c(api) == [{"1": 0}]


def test_permuted_clbits(api):
    """Counts of a circuit that measures qubit 0 into clbit 1 and qubit 1 into clbit 0"""
    qc = QuantumCircuit(2, 2)
    qc.x(0)
    qc.measure(0, 1)
    qc.measure(1, 0)

    result = _run_with_memory(api, [qc], memory=[["0x2", "0x2"]])

    assert result.get_counts() == {"10": 2}
    assert _get_uploaded_q_to_c(api) == [{"0": 1, "1": 0}]


def test_two_circuits_in_one_job(api):
    """Each circuit of a job gets its own counts, of its own width"""
    bell = QuantumCircuit(2, 2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure([0, 1], [0, 1])
    partial = QuantumCircuit(2, 1)
    partial.measure(1, 0)

    result = _run_with_memory(
        api, [bell, partial], memory=[["0x3", "0x0"], ["0x0", "0x0"]]
    )

    assert result.get_counts(0) == {"11": 1, "00": 1}
    assert result.get_counts(1) == {"0": 2}


def test_iq_points(api):
    """meas_level=1 memory is each shot's IQ point per measured qubit, as the backend sent it"""
    qc = QuantumCircuit(2, 2)
    qc.measure([0, 1], [0, 1])

    result = _run_with_memory(
        api, [qc], memory=[_IQ_SHOTS], meas_level=1, meas_return="single"
    )

    np.testing.assert_array_equal(
        result.get_memory(0), [[0.5 - 0.25j, 1.5 + 2.0j], [-1.0 + 0.75j, 0.125j]]
    )


def test_averaged_iq_points(api):
    """meas_level=1 with meas_return=avg gives one IQ point per measured qubit"""
    qc = QuantumCircuit(2, 2)
    qc.measure([0, 1], [0, 1])

    result = _run_with_memory(
        api,
        [qc],
        memory=[[[[0.5, -0.25], [1.5, 2.0]]]],
        meas_level=1,
        meas_return="avg",
    )

    np.testing.assert_array_equal(result.get_memory(0), [0.5 - 0.25j, 1.5 + 2.0j])


@pytest.mark.parametrize("meas_return", [None, "avg"])
def test_counts_ask_for_every_shot(api, meas_return):
    """meas_level=2 sends meas_return=single, so the backend returns each shot's bits"""
    qc = QuantumCircuit(1, 1)
    qc.measure(0, 0)
    options = {} if meas_return is None else {"meas_return": meas_return}

    _run_with_memory(api, [qc], memory=[["0x0", "0x1"]], **options)

    assert _get_uploaded_qobj(api)["config"]["meas_return"] == "single"


def _run_with_memory(
    api,
    circuits: List[QuantumCircuit],
    memory: List[Any],
    meas_level: int = 2,
    **options: Any,
):
    """Runs the circuits on the mocked backend, which answers with the given memory"""
    backend = Tergite.use_provider_account(
        service_name="test", url=API_URL
    ).get_backend(BACKEND_NAME)
    job = backend.run(
        transpile(circuits, backend=backend), meas_level=meas_level, **options
    )
    api.get(f"{API_URL}/jobs/{TEST_JOB_ID}").respond(
        json={
            "job_id": TEST_JOB_ID,
            "device": BACKEND_NAME,
            "calibration_date": TEST_CALIBRATIONS_MAP[BACKEND_NAME]["last_calibrated"],
            "status": "successful",
            "result": {"memory": memory},
        },
    )
    return job.result()


def _get_uploaded_q_to_c(api) -> List[Dict[str, int]]:
    """The qubit-to-clbit map of each experiment, as the pulse payload carries it"""
    qobj = _get_uploaded_qobj(api)
    return [
        exp["header"]["metadata"]["tergite"]["q_to_c"] for exp in qobj["experiments"]
    ]


def _get_uploaded_qobj(api) -> Dict[str, Any]:
    """The qobj the job uploaded to the backend"""
    upload = next(
        req
        for req in (call.request for call in api.calls)
        if req.method == "POST"
        and req.url.path == "/jobs"
        and b"upload_file" in req.content
    )
    return extract_uploaded_qobj_from_request(upload)
