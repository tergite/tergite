# This code is part of Tergite
#
# (C) Copyright Martin Ahindura 2023
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""tests for running circuits on a tergite backend, and for the jobs that run them"""
import json

import pytest
from qiskit import QuantumCircuit, qasm3, transpile
from qiskit.providers import JobStatus

from tergite import Tergite, TergiteBackend
from tergite.exc import ApiError, JobFailedError, TergiteError
from tests.utils.uploads import get_uploaded_job_file

from .conftest import (
    API_TOKEN,
    API_URL,
    GOOD_BACKENDS,
    INVALID_API_TOKENS,
    TEST_CALIBRATIONS_MAP,
    TEST_JOB_ID,
    TEST_JOB_RESULTS,
)

# a refused token is refused alike on every backend, so one backend is enough
_INVALID_TOKENS = [pytest.param(token, id=token) for token in INVALID_API_TOKENS]


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_run_uploads_the_circuits_as_openqasm3(api, backend_name):
    """run() registers the job at MSS and uploads its transpiled circuits in OpenQASM 3"""
    backend = _get_backend(backend_name)
    circuit = _get_x_circuit(backend)

    job = backend.run(circuit, shots=123)

    job_file = get_uploaded_job_file(api)
    assert job.job_id() == job_file.job_id == TEST_JOB_ID
    assert [c.qasm for c in job_file.params.circuits] == [qasm3.dumps(circuit)]
    assert [c.num_clbits for c in job_file.params.circuits] == [1]
    assert (job_file.params.shots, job_file.params.meas_level) == (123, 2)
    assert job_file.params.meas_return == "single"


def test_run_takes_the_backends_options(api):
    """run() uses the backend's options where it is not given them"""
    backend = _get_backend("loke")
    backend.set_options(shots=77, meas_level=1, meas_return="avg")

    backend.run(_get_x_circuit(backend))

    params = get_uploaded_job_file(api).params
    assert (params.shots, params.meas_level, params.meas_return) == (77, 1, "avg")


def test_run_several_circuits_as_one_job(api):
    """run() of a list of circuits uploads them all in one job, in order"""
    backend = _get_backend("loke")
    circuits = [_get_x_circuit(backend), _get_x_circuit(backend)]
    circuits[1].name = "second"

    backend.run(circuits)

    names = [c.name for c in get_uploaded_job_file(api).params.circuits]
    assert names == [circuits[0].name, "second"]


def test_run_refuses_an_untranspiled_circuit(api):
    """run() of a circuit with gates the target lacks raises before registering a job"""
    backend = _get_backend("loke")
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)

    with pytest.raises(TergiteError, match="has no h on qubits"):
        backend.run(circuit)

    assert [call for call in api.calls if call.request.method == "POST"] == []


@pytest.mark.parametrize("run_input", [42, [42]], ids=["alone", "in-a-list"])
def test_run_refuses_what_is_neither_a_circuit_nor_a_program(api, run_input):
    """run() of anything but circuits and OpenQASM 3 programs raises before registering a
    job"""
    backend = _get_backend("loke")

    with pytest.raises(
        TergiteError, match="run circuits or OpenQASM 3 programs, not int"
    ):
        backend.run(run_input)

    assert [call for call in api.calls if call.request.method == "POST"] == []


def test_run_keeps_the_target_of_the_same_calibration(api):
    """run() rebuilds no target while the device's calibration is the one it was built from"""
    backend = _get_backend("loke")
    target = backend.target

    backend.run(_get_x_circuit(backend))

    assert backend.target is target


def test_run_rebuilds_the_target_of_a_new_calibration(api, monkeypatch):
    """run() rebuilds the target once the device is calibrated again, and registers the job
    as compiled with that calibration"""
    backend = _get_backend("loke")
    target = backend.target
    circuit = _get_x_circuit(backend)
    calibration = {
        **TEST_CALIBRATIONS_MAP["loke"],
        "last_calibrated": "2099-01-01T00:00",
    }
    monkeypatch.setitem(TEST_CALIBRATIONS_MAP, "loke", calibration)

    backend.run(circuit)

    assert backend.target is not target
    [created] = [c.request for c in api.calls if c.request.url.path == "/jobs/"]
    assert json.loads(created.content)["calibration_date"] == "2099-01-01T00:00"


def test_run_bearer_auth(bearer_auth_api):
    """run() sends the app token to MSS and the job's token to the backend"""
    backend = _get_backend("loke", token=API_TOKEN)

    job = backend.run(_get_x_circuit(backend))

    assert job.job_id() == TEST_JOB_ID


@pytest.mark.parametrize("token", _INVALID_TOKENS)
def test_run_invalid_bearer_auth(bearer_auth_api, token):
    """run() with a refused app token raises the API's refusal"""
    backend = _get_backend("loke", token=API_TOKEN)
    circuit = _get_x_circuit(backend)
    backend.provider.account.token = token

    with pytest.raises(ApiError, match="Unauthorized"):
        backend.run(circuit)


@pytest.mark.parametrize("api_fixture", ["api", "bearer_auth_api"])
def test_job_status_result_and_download_url(api_fixture, request):
    """A successful job's status is DONE, its result has the counts of its memory"""
    request.getfixturevalue(api_fixture)
    backend = _get_backend("loke", token=API_TOKEN)
    job = backend.run(_get_x_circuit(backend), shots=100)

    assert job.status() == JobStatus.DONE
    assert job.result().get_counts() == {"1": 50, "0": 50}
    assert job.download_url == TEST_JOB_RESULTS["download_url"]


@pytest.mark.parametrize("token", _INVALID_TOKENS)
def test_job_status_invalid_bearer_auth(bearer_auth_api, token):
    """job.status() with a refused app token raises the API's refusal"""
    backend = _get_backend("loke", token=API_TOKEN)
    job = backend.run(_get_x_circuit(backend))
    backend.provider.account.token = token

    with pytest.raises(ApiError, match="error retrieving job data: Unauthorized"):
        job.status()


@pytest.mark.parametrize("api_fixture", ["api", "bearer_auth_api"])
def test_job_cancel(api_fixture, request):
    """job.cancel() asks the backend to cancel the job, with the job's token"""
    router = request.getfixturevalue(api_fixture)
    backend = _get_backend("loke", token=API_TOKEN)
    job = backend.run(_get_x_circuit(backend))

    job.cancel()

    cancel = router.calls[-1].request
    assert (cancel.method, cancel.url.path) == ("POST", f"/jobs/{TEST_JOB_ID}/cancel")
    assert cancel.headers["Authorization"] == "Bearer ACCESS_TOKEN"


@pytest.mark.parametrize("api_fixture", ["api", "bearer_auth_api"])
def test_job_logfile(api_fixture, request, tmp_results_file):
    """job.logfile downloads the finished job's logfile into the temporary folder"""
    request.getfixturevalue(api_fixture)
    backend = _get_backend("loke", token=API_TOKEN)
    job = backend.run(_get_x_circuit(backend))

    assert job.logfile == tmp_results_file
    assert tmp_results_file.read_bytes()


def test_provider_job(api):
    """provider.job(job_id) gets the job from MSS, with the counts of its memory"""
    api.get(f"{API_URL}/jobs/{TEST_JOB_ID}").respond(
        json={
            **TEST_JOB_RESULTS,
            "job_id": TEST_JOB_ID,
            "device": "loke",
            "calibration_date": TEST_CALIBRATIONS_MAP["loke"]["last_calibrated"],
        }
    )
    provider = Tergite.use_provider_account(service_name="test", url=API_URL)

    job = provider.job(TEST_JOB_ID)

    assert job.status() == JobStatus.DONE
    assert job.result().get_counts() == {"1": 50, "0": 50}


@pytest.mark.parametrize(
    "status, reason_field, message",
    [
        ("failed", "failure_reason", "failed: out of memory"),
        ("cancelled", "cancellation_reason", "was cancelled: out of memory"),
    ],
)
def test_job_result_of_unsuccessful_job(api, status, reason_field, message):
    """job.result() of a failed or cancelled job raises with the job's reason"""
    backend = _get_backend("loke")
    job = backend.run(_get_x_circuit(backend))
    api.get(f"{API_URL}/jobs/{TEST_JOB_ID}").respond(
        json={
            "job_id": TEST_JOB_ID,
            "device": "loke",
            "calibration_date": TEST_CALIBRATIONS_MAP["loke"]["last_calibrated"],
            "status": status,
            reason_field: "out of memory",
        },
    )

    with pytest.raises(JobFailedError, match=f"Job {TEST_JOB_ID} {message}"):
        job.result()


def test_every_call_has_a_timeout(api, tmp_results_file):
    """Every call to MSS or BCC gives up after a timeout, so an unresponsive server cannot hang the caller"""
    backend = _get_backend("loke")
    job = backend.run(_get_x_circuit(backend))
    assert job.logfile == tmp_results_file
    job.cancel()

    timeouts = {
        (req.method, req.url.host, req.url.path): req.extensions["timeout"]["read"]
        for req in (call.request for call in api.calls)
    }
    assert {
        ("GET", "api.tergite.example", "/devices/"),
        ("GET", "api.tergite.example", "/calibrations/loke"),
        ("POST", "api.tergite.example", "/jobs/"),
        ("GET", "api.tergite.example", "/jobs/test_job_id"),
        ("POST", "loke.tergite.example", "/jobs"),
        ("GET", "loke.tergite.example", "/test_file.hdf5"),
        ("POST", "loke.tergite.example", "/jobs/test_job_id/cancel"),
    } <= timeouts.keys()
    assert None not in timeouts.values()


def _get_backend(name: str, token: str = None) -> TergiteBackend:
    """Gets the backend of the given name through a new test provider"""
    provider = Tergite.use_provider_account(
        service_name="test", url=API_URL, token=token
    )
    return provider.get_backend(name)


def _get_x_circuit(backend: TergiteBackend) -> QuantumCircuit:
    """Gets an X on qubit 0, measured, transpiled to the backend"""
    circuit = QuantumCircuit(1, 1)
    circuit.x(0)
    circuit.measure(0, 0)
    return transpile(circuit, backend=backend, initial_layout=[0])
