# This code is part of Tergite
#
# (C) Copyright Martin Ahindura 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""tests for the running of qiskit circuits on the tergite backend"""
import json
import uuid
import warnings
from collections import Counter
from typing import List, Optional

import numpy as np
import pytest
from qiskit import QuantumCircuit, circuit, compiler, pulse
from qiskit.providers import JobStatus
from qiskit.result import Result
from qiskit.result.models import ExperimentResult, ExperimentResultData

from tergite import Job, OpenPulseBackend, Provider, Tergite

# cross compatibility with future qiskit version where deprecated packages are removed
from tergite.compat.qiskit.compiler.assembler import assemble
from tergite.services.api_client.dtos import DeviceCalibration, TergiteBackendConfig
from tergite.services.device_compiler.schedules import cz
from tests.utils.records import get_record
from tests.utils.requests import MockRequest, get_request_list

from ..utils.env import is_end_to_end
from .conftest import (
    API_TOKEN,
    API_URL,
    BACKENDS_LIST,
    GOOD_BACKENDS,
    INVALID_API_TOKENS,
    NUMBER_OF_SHOTS,
    QUANTUM_COMPUTER_URL,
    TEST_CALIBRATIONS_MAP,
    TEST_JOB_ID,
    TEST_JOB_RESULTS,
    TEST_QOBJ_ID,
    TEST_QOBJ_RESULTS_MAP,
    TWO_QUBIT_BACKENDS,
)

_INVALID_PARAMS = [
    (token, backend) for backend in GOOD_BACKENDS for token in INVALID_API_TOKENS
]


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_transpile_1q_gates(api, backend_name):
    """compiler.transpile(qc, backend=backend) returns backend-specific QuantumCircuits for 1-qubit ops"""
    backend = _get_backend(name=backend_name)
    calibrations = _get_calibrations(backend_name)
    qc = _get_test_1q_qiskit_circuit()

    # Transpile the circuit
    got = compiler.transpile(qc, backend=backend, initial_layout=qc.qubits)
    expected = _get_expected_1q_transpiled_circuit(
        backend=backend, calibrations=calibrations, circuit_name=got.name
    )

    got_qobj = backend.make_qobj(got)
    expected_qobj = backend.make_qobj(expected, qobj_id=got_qobj.qobj_id)

    assert (
        got_qobj == expected_qobj
    ), "Transpiled circuit does not match expected result."


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", TWO_QUBIT_BACKENDS)
def test_transpile_2q_gates(api, backend_name):
    """compiler.transpile(qc, backend=backend) returns backend-specific QuantumCircuits for 2-qubit gate ops"""
    backend = _get_backend(name=backend_name)
    calibrations = _get_calibrations(backend_name)
    qc = _get_test_2q_qiskit_circuit()
    expected = _get_expected_2q_transpiled_circuit(
        backend=backend, calibrations=calibrations, circuit_name=qc.name
    )

    # Transpile the circuit
    got = compiler.transpile(qc, backend=backend, initial_layout=qc.qubits)

    got_qobj = backend.make_qobj(got)
    expected_qobj = backend.make_qobj(expected, qobj_id=got_qobj.qobj_id)

    assert (
        got_qobj == expected_qobj
    ), "Transpiled circuit does not match expected result."


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_run_1q_gates(api, backend_name):
    """backend.run returns a registered job for 1-qubit gate operations"""
    backend = _get_backend(backend_name)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    backend.set_options(shots=NUMBER_OF_SHOTS)
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    qobj_id = str(uuid.uuid4())
    expected = _get_expected_job(
        backend=backend, transpiled_circuit=tc, meas_level=2, qobj_id=qobj_id
    )
    expected._calibration_date = calibration_date

    got = backend.run(tc, meas_level=2, qobj_id=qobj_id)
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[:4]

    assert got == expected
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", TWO_QUBIT_BACKENDS)
def test_run_2q_gates(api, backend_name):
    """backend.run returns a registered job for 2-qubit gate operations"""
    backend = _get_backend(backend_name)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    backend.set_options(shots=NUMBER_OF_SHOTS)
    tc = _get_expected_2q_transpiled_circuit(backend=backend, calibrations=calibrations)
    qobj_id = str(uuid.uuid4())
    expected = _get_expected_job(
        backend=backend, transpiled_circuit=tc, meas_level=2, qobj_id=qobj_id
    )
    expected._calibration_date = calibration_date

    got = backend.run(tc, meas_level=2, qobj_id=qobj_id)
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[:4]

    assert got == expected
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_run_bearer_auth(bearer_auth_api, backend_name):
    """backend.run returns a registered job for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    backend.set_options(shots=NUMBER_OF_SHOTS)
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    qobj_id = str(uuid.uuid4())
    expected = _get_expected_job(
        backend=backend, transpiled_circuit=tc, meas_level=2, qobj_id=qobj_id
    )
    expected._calibration_date = calibration_date

    got = backend.run(tc, meas_level=2, qobj_id=qobj_id)
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[:4]

    assert got == expected
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_run_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """backend.run with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=token)
    backend.set_options(shots=NUMBER_OF_SHOTS)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    qobj_id = str(uuid.uuid4())

    with pytest.raises(
        RuntimeError,
        match=f"failed to get device calibrations for '{backend_name}': Unauthorized",
    ):
        _ = backend.run(tc, meas_level=2, qobj_id=qobj_id)

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:2]

    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_result(api, backend_name):
    """job.result() returns a successful job's results"""
    backend = _get_backend(backend_name)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    expected = _get_expected_job_result(backend=backend, job=job)

    got = job.result()
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert got.to_dict() == expected.to_dict()
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_result_bearer_auth(bearer_auth_api, backend_name):
    """job.result() returns a successful job's results for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    expected = _get_expected_job_result(backend=backend, job=job)
    got = job.result()
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert got.to_dict() == expected.to_dict()
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_result_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.result() with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    # change the token to the invalid one
    backend.provider.account.token = token

    with pytest.raises(RuntimeError, match=f"error retrieving job data: Unauthorized"):
        _ = job.result()

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_status(api, backend_name):
    """job.status() returns a successful job's status"""
    backend = _get_backend(backend_name)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    got = job.status()
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert got == JobStatus.DONE
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_status_bearer_auth(bearer_auth_api, backend_name):
    """job.status() returns a successful job's status for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    got = job.status()
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert got == JobStatus.DONE
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_status_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.status() with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    # change the token to the invalid one
    backend.provider.account.token = token

    with pytest.raises(RuntimeError, match=f"error retrieving job data: Unauthorized"):
        _ = job.status()

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_cancel(api, backend_name):
    """job.cancel() cancels the running job"""
    backend = _get_backend(backend_name)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)
    job.cancel()

    mock_cancel_request = _get_mock_cancel_request(job)
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:4] + [mock_cancel_request]

    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_cancel_bearer_auth(bearer_auth_api, backend_name):
    """job.cancel() calls the cancel endpoint for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)
    job.cancel()

    mock_cancel_request = _get_mock_cancel_request(job)
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:4] + [mock_cancel_request]

    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_cancel_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.cancel() with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)
    job_id = job.job_id()

    # change the token to the invalid one
    backend.provider.account.token = token

    with pytest.raises(
        RuntimeError, match=f"Failed to cancel job '{job_id}': Unauthorized"
    ):
        _ = job.cancel()

    mock_cancel_request = _get_mock_cancel_request(job)
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:4] + [mock_cancel_request]

    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_download_url(api, backend_name):
    """job.download_url returns a successful job's download_url"""
    backend = _get_backend(backend_name)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    got = job.download_url
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert got == TEST_JOB_RESULTS["download_url"]
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_download_url_bearer_auth(bearer_auth_api, backend_name):
    """job.download_url returns a successful job's download_url for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    got = job.download_url
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert got == TEST_JOB_RESULTS["download_url"]
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_download_url_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.download_url with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    # change the token to the invalid one
    backend.provider.account.token = token

    with pytest.raises(RuntimeError, match=f"error retrieving job data: Unauthorized"):
        _ = job.download_url

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_logfile(api, backend_name, tmp_results_file):
    """job.logfile downloads a job's data to tmp"""
    backend = _get_backend(backend_name)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    assert job.logfile == tmp_results_file
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:6]

    with open(tmp_results_file, "rb") as file:
        got = json.load(file)

    assert got == TEST_JOB_RESULTS
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_logfile_bearer_auth(bearer_auth_api, backend_name, tmp_results_file):
    """job.logfile downloads a successful job's results for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    assert job.logfile == tmp_results_file
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:6]

    with open(tmp_results_file, "rb") as file:
        got = json.load(file)

    assert got == TEST_JOB_RESULTS
    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_logfile_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.logfile with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    calibrations = _get_calibrations(backend_name)
    calibration_date = calibrations.last_calibrated
    tc = _get_expected_1q_transpiled_circuit(backend=backend, calibrations=calibrations)
    job = backend.run(tc, meas_level=2)

    # change the token to the invalid one
    backend.provider.account.token = token

    with pytest.raises(RuntimeError, match=f"error retrieving job data: Unauthorized"):
        _ = job.logfile

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(
        backend_name, calibration_date=calibration_date
    )[1:5]

    assert requests_made == expected_requests


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_provider_job(api_with_logfile, backend_name):
    """Test that Provider.job() returns the correct Job object."""
    provider = Tergite.use_provider_account(service_name="test", url=API_URL)

    # create a job the usual way
    backend = _get_backend(backend_name, provider=provider)
    backend.set_options(shots=NUMBER_OF_SHOTS)
    calibrations = _get_calibrations(backend_name)
    qobj_id = f"{TEST_QOBJ_ID}-{backend_name}"
    circuit_name = TEST_QOBJ_RESULTS_MAP[backend_name.lower()]["experiments"][0][
        "header"
    ]["name"]

    tc = _get_expected_1q_transpiled_circuit(
        backend=backend, calibrations=calibrations, circuit_name=circuit_name
    )
    expected = backend.run(tc, meas_level=2, qobj_id=qobj_id)

    assert expected.logfile is not None
    # overwrite some properties that are expected to change when getting job by job id
    expected.upload_url = expected.metadata["upload_url"] = None
    job_id = expected.job_id()

    # retrieve job from provider
    got = provider.job(job_id)

    assert got == expected, "The retrieved job does not match the original job."


def _get_expected_job_result(backend: OpenPulseBackend, job: Job) -> Result:
    """Returns the expected job result"""
    results = [
        ExperimentResult(
            header=job.payload.experiments[index].header,
            shots=job.metadata["shots"],
            success=True,
            data=ExperimentResultData(
                counts=dict(Counter(result)),
                memory=result,
            ),
        )
        for index, result in enumerate(TEST_JOB_RESULTS["result"]["memory"])
    ]

    return Result(
        backend_name=backend.name,
        backend_version=backend.backend_version,
        qobj_id=job.metadata["qobj_id"],
        job_id=job.job_id(),
        success=True,
        results=results,
    )


def _get_expected_job(
    backend: OpenPulseBackend,
    transpiled_circuit: QuantumCircuit,
    qobj_id: str,
    **options,
) -> Job:
    """Returns the expected job after being initialized"""
    schedule = compiler.schedule(transpiled_circuit, backend=backend)
    with warnings.catch_warnings():
        # The class QobjExperimentHeader is deprecated
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="qiskit")
        qobj = assemble(
            experiments=[schedule],
            backend=backend,
            shots=NUMBER_OF_SHOTS,
            qubit_lo_freq=backend.qubit_lo_freq,
            meas_lo_freq=backend.meas_lo_freq,
            qobj_id=qobj_id,
            **options,
        )

    job = Job(
        backend=backend,
        job_id=TEST_JOB_ID,
        payload=qobj,
        upload_url=f"{QUANTUM_COMPUTER_URL}/jobs",
    )

    job.metadata["shots"] = NUMBER_OF_SHOTS
    job.metadata["qobj_id"] = qobj_id
    job.metadata["num_experiments"] = 1

    return job


def _get_test_1q_qiskit_circuit():
    """Returns a qiskit quantum circuit for testing two qubit gates"""
    qc = circuit.QuantumCircuit(1)
    qc.h(0)
    qc.measure_all()
    return qc


def _get_test_2q_qiskit_circuit():
    """Returns a qiskit quantum circuit for testing for testing one qubit gate"""
    qc = circuit.QuantumCircuit(2)
    qc.h(0)
    qc.h(1)
    qc.cx(0, 1)
    qc.measure_all()
    return qc


def _get_expected_1q_transpiled_circuit(
    backend: OpenPulseBackend,
    calibrations: DeviceCalibration,
    circuit_name: Optional[str] = None,
) -> circuit.QuantumCircuit:
    """Returns a quantum circuit for 1-qubit gates specific to the TEST_BACKEND

    Args:
        backend: the backend for which the circuit is transpiled
        calibrations: the device parameters for the given backend
        circuit_name: the name of the expected circuit

    Returns:
        The circuit.QuantumCircuit that corresponds to the 1-qubit gate example
    """
    phase = np.pi / 2
    qc = circuit.QuantumCircuit(1, global_phase=phase, name=circuit_name)
    qc.rz(phase, 0)
    qc.rx(phase, 0)
    qc.rz(phase, 0)
    qc.measure_all()

    # initialize calibrations
    qubit_0 = calibrations.qubits[0]

    rz_block = pulse.ScheduleBlock(
        name="RZ(λ, (0,))",
        alignment_context=pulse.transforms.AlignLeft(),
    )
    rz_block.append(
        pulse.ShiftPhase(round(phase, 10), pulse.DriveChannel(0), name="RZ q0")
    )

    rx_block = pulse.ScheduleBlock(
        name="RX(θ, (0,))",
        alignment_context=pulse.transforms.AlignLeft(),
    )
    rx_block.append(pulse.SetFrequency(qubit_0.frequency.value, pulse.DriveChannel(0)))
    rx_block.append(
        pulse.Play(
            # amp represents the magnitude of the complex amplitude and can't be complex
            pulse.Gaussian(
                duration=round(qubit_0.pi_pulse_duration.value / backend.dt),
                amp=round(phase / np.pi * qubit_0.pi_pulse_amplitude.value, 10),
                sigma=round(qubit_0.pulse_sigma.value / backend.dt),
                name="RX q0",
            ),
            pulse.DriveChannel(0),
            name="RX q0",
        )
    )

    qc._calibrations = {
        "rz": {((0,), (phase,)): rz_block},
        "rx": {((0,), (phase,)): rx_block},
    }

    return qc


def _get_expected_2q_transpiled_circuit(
    backend: OpenPulseBackend,
    calibrations: DeviceCalibration,
    circuit_name: Optional[str] = None,
):
    """Returns a quantum circuit for 2-qubit gates specific to the TEST_BACKEND

    Args:
        backend: the backend for which the circuit is transpiled
        calibrations: the device parameters for the given backend
        circuit_name: the name of the expected circuit

    Returns:
        The circuit.QuantumCircuit that corresponds to the 2-qubit gate example
    """
    phase = np.pi / 2
    qc = circuit.QuantumCircuit(2, global_phase=np.pi, name=circuit_name)
    qc.rz(phase, 0)
    qc.rx(phase, 0)
    qc.rz(phase, 0)

    qc.cz(0, 1)

    qc.rz(phase, 1)
    qc.rx(phase, 1)
    qc.rz(phase, 1)

    qc.measure_all()

    ##
    qubit_0 = calibrations.qubits[0]
    qubit_1 = calibrations.qubits[1]

    # initialize calibrations
    # rz_block_0
    rz_block_0 = pulse.ScheduleBlock(
        name="RZ(λ, (0,))",
        alignment_context=pulse.transforms.AlignLeft(),
    )
    rz_block_0.append(
        pulse.ShiftPhase(round(phase, 10), pulse.DriveChannel(0), name="RZ q0")
    )

    # rz_block_1
    rz_block_1 = pulse.ScheduleBlock(
        name="RZ(λ, (1,))",
        alignment_context=pulse.transforms.AlignLeft(),
    )
    rz_block_1.append(
        pulse.ShiftPhase(round(phase, 10), pulse.DriveChannel(1), name="RZ q1")
    )

    # rx_block_0
    rx_block_0 = pulse.ScheduleBlock(
        name="RX(θ, (0,))",
        alignment_context=pulse.transforms.AlignLeft(),
    )
    rx_block_0.append(
        pulse.SetFrequency(qubit_0.frequency.value, pulse.DriveChannel(0))
    )
    rx_block_0.append(
        pulse.Play(
            # amp represents the magnitude of the complex amplitude and can't be complex
            pulse.Gaussian(
                duration=round(qubit_0.pi_pulse_duration.value / backend.dt),
                amp=round(phase / np.pi * qubit_0.pi_pulse_amplitude.value, 10),
                sigma=round(qubit_0.pulse_sigma.value / backend.dt),
                name="RX q0",
            ),
            pulse.DriveChannel(0),
            name="RX q0",
        )
    )

    # rx_block_1
    rx_block_1 = pulse.ScheduleBlock(
        name="RX(θ, (1,))",
        alignment_context=pulse.transforms.AlignLeft(),
    )
    rx_block_1.append(
        pulse.SetFrequency(qubit_1.frequency.value, pulse.DriveChannel(1))
    )
    rx_block_1.append(
        pulse.Play(
            # amp represents the magnitude of the complex amplitude and can't be complex
            pulse.Gaussian(
                duration=round(qubit_1.pi_pulse_duration.value / backend.dt),
                amp=round(phase / np.pi * qubit_1.pi_pulse_amplitude.value, 10),
                sigma=round(qubit_1.pulse_sigma.value / backend.dt),
                name="RX q1",
            ),
            pulse.DriveChannel(1),
            name="RX q1",
        )
    )

    # cz_block
    cz_block = cz(
        backend=backend,
        control_qubit_idxs=(0,),
        target_qubit_idxs=(1,),
        device_properties=calibrations,
    )

    qc._calibrations = {
        "cz": {((0, 1), ()): cz_block},
        "rz": {((0,), (phase,)): rz_block_0, ((1,), (phase,)): rz_block_1},
        "rx": {((0,), (phase,)): rx_block_0, ((1,), (phase,)): rx_block_1},
    }

    return qc


def _get_backend(name: str, token: str = None, provider: Optional[Provider] = None):
    """Retrieves the right backend

    Args:
        name: the name of the backend
        token: the API token to use to access the API; defaults to None
        provider: an optional provider to use; defaults to None

    Returns:
        An OpenPulseBackend corresponding to the given name
    """
    if provider is None:
        provider = Tergite.use_provider_account(
            service_name="test", url=API_URL, token=token
        )

    expected_json = get_record(BACKENDS_LIST, _filter={"name": name})
    return OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )


def _get_calibrations(backend_name: str) -> DeviceCalibration:
    """Retrieves the device calibrations for the given device

    Args:
        backend_name: the name of the device

    Returns:
        the DeviceCalibration of the given device
    """
    data = TEST_CALIBRATIONS_MAP[backend_name]
    return DeviceCalibration(**data)


def _get_all_mock_requests(
    backend_name: str, calibration_date: Optional[str] = None
) -> List[MockRequest]:
    """Generates all the possible mock requests for a given backend

    Args:
        backend_name: the name of the backend

    Returns:
        The list of all MockRequests for the given backend name
    """
    return [
        MockRequest(
            url=f"https://api.tergite.example/calibrations/{backend_name}",
            method="GET",
        ),
        MockRequest(
            url=f"https://api.tergite.example/calibrations/{backend_name}",
            method="GET",
        ),
        MockRequest(
            url=f"https://api.tergite.example/jobs/",
            method="POST",
            json={"device": backend_name, "calibration_date": calibration_date},
            has_text=True,
        ),
        MockRequest(
            url="http://loke.tergite.example/jobs", method="POST", has_text=True
        ),
        MockRequest(
            url="https://api.tergite.example/jobs/test_job_id",
            method="GET",
            has_text=False,
        ),
        MockRequest(url="http://loke.tergite.example/test_file.hdf5", method="GET"),
    ]


def _get_mock_cancel_request(job: Job) -> MockRequest:
    """Gets the mock cancel request for the given job

    Args:
        job: the job to cancel

    Returns:
        the MockRequest
    """
    return MockRequest(
        url=f"http://loke.tergite.example/jobs/{job.job_id()}/cancel",
        method="POST",
        json={},
        has_text=True,
    )
