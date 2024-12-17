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
from typing import List

import numpy as np
import pytest
from qiskit import QuantumCircuit, circuit, compiler, pulse
from qiskit.providers import JobStatus
from qiskit.result import Result
from qiskit.result.models import ExperimentResult, ExperimentResultData

# cross compatibility with future qiskit version where deprecated packages are removed
from tergite.qiskit.deprecated.compiler.assembler import assemble
from tergite.qiskit.providers import Job, OpenPulseBackend, Tergite
from tergite.qiskit.providers.backend import TergiteBackendConfig
from tergite.qiskit.providers.provider_account import ProviderAccount
from tests.conftest import (
    API_TOKEN,
    API_URL,
    BACKENDS_LIST,
    GOOD_BACKENDS,
    INVALID_API_TOKENS,
    NUMBER_OF_SHOTS,
    QUANTUM_COMPUTER_URL,
    TEST_JOB_ID,
    TEST_JOB_RESULTS,
)
from tests.utils.quantum_circuits import remove_idle_qubits
from tests.utils.records import get_record
from tests.utils.requests import MockRequest, get_request_list

_INVALID_PARAMS = [
    (token, backend) for backend in GOOD_BACKENDS for token in INVALID_API_TOKENS
]


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_transpile(api, backend_name):
    """compiler.transpile(qc, backend=backend) returns backend-specific QuantumCircuits"""
    backend = _get_backend(name=backend_name)
    qc = _get_test_qiskit_circuit()
    expected = _get_expected_transpiled_circuit()

    # Transpile the circuit
    got = compiler.transpile(qc, backend=backend, initial_layout=qc.qubits)

    # Remove idle qubits from the circuit, otherwise comparison fails even though active parts are equivalent
    got = remove_idle_qubits(got)
    expected = remove_idle_qubits(expected)

    # Compare the circuits appropriately
    assert str(got) == str(
        expected
    ), "Transpiled circuit does not match expected result."


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_run(api, backend_name):
    """backend.run returns a registered job"""
    backend = _get_backend(backend_name)
    backend.set_options(shots=NUMBER_OF_SHOTS)
    tc = _get_expected_transpiled_circuit()
    qobj_id = str(uuid.uuid4())
    expected = _get_expected_job(
        backend=backend, transpiled_circuit=tc, meas_level=2, qobj_id=qobj_id
    )

    got = backend.run(tc, meas_level=2, qobj_id=qobj_id)
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(backend_name)[:14]

    assert got == expected
    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_run_bearer_auth(bearer_auth_api, backend_name):
    """backend.run returns a registered job for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    backend.set_options(shots=NUMBER_OF_SHOTS)
    tc = _get_expected_transpiled_circuit()
    qobj_id = str(uuid.uuid4())
    expected = _get_expected_job(
        backend=backend, transpiled_circuit=tc, meas_level=2, qobj_id=qobj_id
    )

    got = backend.run(tc, meas_level=2, qobj_id=qobj_id)
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[:14]

    assert got == expected
    assert requests_made == expected_requests


@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_run_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """backend.run with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=token)
    backend.set_options(shots=NUMBER_OF_SHOTS)
    tc = _get_expected_transpiled_circuit()
    qobj_id = str(uuid.uuid4())

    with pytest.raises(RuntimeError, match="Unable to register job at the Tergite MSS"):
        _ = backend.run(tc, meas_level=2, qobj_id=qobj_id)

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:7]

    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_result(api, backend_name):
    """job.result() returns a successful job's results"""
    backend = _get_backend(backend_name)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    expected = _get_expected_job_result(backend=backend, job=job)

    got = job.result()
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(backend_name)[6:16]

    assert got.to_dict() == expected.to_dict()
    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_result_bearer_auth(bearer_auth_api, backend_name):
    """job.result() returns a successful job's results for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    expected = _get_expected_job_result(backend=backend, job=job)
    got = job.result()
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:16]

    assert got.to_dict() == expected.to_dict()
    assert requests_made == expected_requests


@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_result_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.result() with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    # change the token to the invalid one
    backend.provider.provider_account.token = token

    with pytest.raises(
        RuntimeError, match=f"Failed to GET status of job: {TEST_JOB_ID}"
    ):
        _ = job.result()

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:15]

    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_status(api, backend_name):
    """job.status() returns a successful job's status"""
    backend = _get_backend(backend_name)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    got = job.status()
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(backend_name)[6:15]

    assert got == JobStatus.DONE
    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_status_bearer_auth(bearer_auth_api, backend_name):
    """job.status() returns a successful job's status for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    got = job.status()
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:15]

    assert got == JobStatus.DONE
    assert requests_made == expected_requests


@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_status_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.status() with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    # change the token to the invalid one
    backend.provider.provider_account.token = token

    with pytest.raises(
        RuntimeError, match=f"Failed to GET status of job: {TEST_JOB_ID}"
    ):
        _ = job.status()

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:15]

    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_download_url(api, backend_name):
    """job.download_url returns a successful job's download_url"""
    backend = _get_backend(backend_name)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    got = job.download_url
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(backend_name)[6:16]

    assert got == TEST_JOB_RESULTS["download_url"]
    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_download_url_bearer_auth(bearer_auth_api, backend_name):
    """job.download_url returns a successful job's download_url for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    got = job.download_url
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:16]

    assert got == TEST_JOB_RESULTS["download_url"]
    assert requests_made == expected_requests


@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_download_url_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.download_url with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    # change the token to the invalid one
    backend.provider.provider_account.token = token

    with pytest.raises(
        RuntimeError, match=f"Failed to GET status of job: {TEST_JOB_ID}"
    ):
        _ = job.download_url

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:15]

    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_logfile(api, backend_name, tmp_results_file):
    """job.logfile downloads a job's data to tmp"""
    backend = _get_backend(backend_name)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    assert job.logfile == tmp_results_file
    requests_made = get_request_list(api)
    expected_requests = _get_all_mock_requests(backend_name)[6:17]

    with open(tmp_results_file, "rb") as file:
        got = json.load(file)

    assert got == TEST_JOB_RESULTS
    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_job_logfile_bearer_auth(bearer_auth_api, backend_name, tmp_results_file):
    """job.logfile downloads a successful job's results for API behind bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    assert job.logfile == tmp_results_file
    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:17]

    with open(tmp_results_file, "rb") as file:
        got = json.load(file)

    assert got == TEST_JOB_RESULTS
    assert requests_made == expected_requests


@pytest.mark.parametrize("token, backend_name", _INVALID_PARAMS)
def test_job_logfile_invalid_bearer_auth(token, backend_name, bearer_auth_api):
    """job.logfile with invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    backend = _get_backend(backend_name, token=API_TOKEN)
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    # change the token to the invalid one
    backend.provider.provider_account.token = token

    with pytest.raises(
        RuntimeError, match=f"Failed to GET status of job: {TEST_JOB_ID}"
    ):
        _ = job.logfile

    requests_made = get_request_list(bearer_auth_api)
    expected_requests = _get_all_mock_requests(backend_name)[6:15]

    assert requests_made == expected_requests


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_provider_job(api_with_logfile, backend_name, token: str = None):
    """Test that Provider.job returns the correct Job object."""

    # create a job the usual way
    backend = _get_backend(backend_name)
    transpiled_circuit = _get_expected_transpiled_circuit()
    job = backend.run(transpiled_circuit, meas_level=2)
    job_id = job.job_id()

    # retrieve job from provider
    account = ProviderAccount(service_name=f"test", url=API_URL, token=token)
    provider = Tergite.use_provider_account(account)
    retrieved_job = provider.job(job_id)

    retrieved_result = retrieved_job.result()
    result = job.result()

    assert (
        retrieved_result.get_counts() == result.get_counts()
    ), "The retrieved job result does not match the original job result."


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

    job = Job(backend=backend, job_id=TEST_JOB_ID, upload_url=QUANTUM_COMPUTER_URL)

    job.metadata["shots"] = NUMBER_OF_SHOTS
    job.metadata["qobj_id"] = qobj_id
    job.metadata["num_experiments"] = 1
    job.payload = qobj

    return job


def _get_test_qiskit_circuit():
    """Returns a qiskit quantum circuit for testing"""
    qc = circuit.QuantumCircuit(2, 2)
    qc.h(1)
    qc.measure(1, 1)
    return qc


def _get_expected_transpiled_circuit():
    """Returns a quantum circuit specific to the TEST_BACKEND"""
    phase = np.pi / 2
    qc = circuit.QuantumCircuit(2, 2, global_phase=phase)
    qc.rz(phase, 1)
    qc.rx(phase, 1)
    qc.rz(phase, 1)
    qc.measure(1, 1)

    # initialize calibrations
    rz_block = pulse.ScheduleBlock(
        name="RZ(λ, (1,))",
        alignment_context=pulse.transforms.AlignLeft(),
    )
    rz_block.append(pulse.ShiftPhase(1.5707963268, pulse.DriveChannel(1), name="RZ q1"))

    rx_block = pulse.ScheduleBlock(
        name="RX(θ, (1,))",
        alignment_context=pulse.transforms.AlignLeft(),
    )
    rx_block.append(pulse.SetFrequency(3932312578.2853203, pulse.DriveChannel(1)))
    rx_block.append(
        pulse.Play(
            # amp represents the magnitude of the complex amplitude and can't be complex
            pulse.Gaussian(duration=52, amp=(0.0290173467), sigma=6, name="RX q1"),
            pulse.DriveChannel(1),
            name="RX q1",
        )
    )

    qc._calibrations = {
        "rz": {((1,), (phase,)): rz_block},
        "rx": {((1,), (phase,)): rx_block},
    }

    return qc


def _get_backend(name: str, token: str = None):
    """Retrieves the right backend"""
    account = ProviderAccount(service_name="test", url=API_URL, token=token)
    provider = Tergite.use_provider_account(account)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": name})
    return OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )


def _get_all_mock_requests(backend_name: str) -> List[MockRequest]:
    """Generates all the possible mock requests for a given backend

    Args:
        backend_name: the name of the backend

    Returns:
        The list of all MockRequests for the given backend name
    """
    return [
        *[
            MockRequest(
                url=f"https://api.tergite.example/v2/calibrations/{backend_name}",
                method="GET",
            )
            for _ in range(6)
        ],
        MockRequest(
            url=f"https://api.tergite.example/jobs?backend={backend_name}",
            method="POST",
        ),
        *[
            MockRequest(
                url=f"https://api.tergite.example/v2/calibrations/{backend_name}",
                method="GET",
            )
            for _ in range(6)
        ],
        MockRequest(url="http://loke.tergite.example/", method="POST", has_text=True),
        MockRequest(
            url="https://api.tergite.example/jobs/test_job_id",
            method="GET",
            has_text=False,
        ),
        MockRequest(
            url="https://api.tergite.example/jobs/test_job_id",
            method="GET",
            has_text=False,
        ),
        MockRequest(url="http://loke.tergite.example/test_file.hdf5", method="GET"),
    ]
