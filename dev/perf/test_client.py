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
"""Benchmarks of the SDK alone, against a mocked MSS and backend.

Run by dev/perf/record.sh, which keeps pytest-benchmark's JSON for dev/perf/compare.py. Each
benchmark records, beside its timings, the HTTP calls one round of it made and the peak
memory it allocated, which compare.py holds to the baseline too.
"""
import subprocess
import sys
import tracemalloc
from typing import Callable, List

import pytest
import respx
from qiskit import QuantumCircuit, transpile
from qiskit.providers import JobStatus

from tergite import Job, Tergite, TergiteBackend
from tergite.clients.mss.models import Job as MssJob
from tergite.jobs.results import CircuitHeader
from tests.utils.fixtures import load_json_fixture

API_URL = "https://api.perf.example"
BCC_URL = "http://loke.perf.example"
BACKEND_NAME = "loke"
SHOTS = 10_000


@pytest.fixture
def api():
    """MSS and the backend, mocked with the integration tests' fixtures"""
    with respx.mock(assert_all_called=False) as router:
        devices = load_json_fixture("many_backends.json")
        router.get(f"{API_URL}/devices/").respond(
            json={"data": devices, "skip": 0, "limit": None}
        )
        for calibration in load_json_fixture("calibrations.json"):
            router.get(f"{API_URL}/calibrations/{calibration['name']}").respond(
                json=calibration
            )
        router.post(f"{API_URL}/jobs/").respond(
            json={
                "job_id": "perf",
                "upload_url": f"{BCC_URL}/jobs",
                "access_token": "t",
            }
        )
        router.post(f"{BCC_URL}/jobs").respond(200)
        yield router


def test_import(benchmark):
    """The time a new interpreter takes to import tergite"""
    benchmark.pedantic(
        subprocess.run,
        args=([sys.executable, "-c", "import tergite"],),
        kwargs={"check": True},
        rounds=5,
    )


def test_get_backend(benchmark, api):
    """A new provider's get_backend(), which lists the devices"""
    _record_calls_and_memory(benchmark, api, _get_backend)
    benchmark(_get_backend)


def test_target(benchmark, api):
    """Building a backend's target, which fetches its calibration"""
    _record_calls_and_memory(benchmark, api, lambda: _get_backend().target)
    benchmark(lambda: _get_backend().target)


def test_run(benchmark, api):
    """backend.run() of ten two-qubit circuits, up to the upload"""
    backend = _get_backend()
    circuits = transpile(_get_circuits(10), backend=backend)

    def run() -> None:
        backend.run(circuits, meas_level=2)

    _record_calls_and_memory(benchmark, api, run)
    upload = next(
        call.request for call in api.calls if call.request.url == f"{BCC_URL}/jobs"
    )
    benchmark.extra_info["upload_bytes"] = len(upload.content)
    benchmark(run)


@pytest.mark.parametrize("num_circuits", [1, 10, 100])
def test_result(benchmark, api, num_circuits: int):
    """job.result() of a finished job of 10,000 shots per circuit"""
    backend = _get_backend()
    job = _get_finished_job(backend, num_circuits)

    def get_result() -> None:
        job._result = None
        job.result()

    _record_calls_and_memory(benchmark, api, get_result)
    benchmark(get_result)


def _get_backend() -> TergiteBackend:
    """Gets the benchmarked backend through a new provider"""
    provider = Tergite.use_provider_account(service_name="perf", url=API_URL)
    return provider.get_backend(BACKEND_NAME)


def _get_circuits(count: int) -> List[QuantumCircuit]:
    """Gets that many two-qubit circuits that entangle and measure both qubits"""
    circuits = []
    for _ in range(count):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])
        circuits.append(qc)
    return circuits


def _get_finished_job(backend: TergiteBackend, num_circuits: int) -> Job:
    """Gets a job of that many circuits that MSS reports successful, with its memory"""
    circuits = transpile(_get_circuits(num_circuits), backend=backend)
    remote_data = MssJob(
        device=BACKEND_NAME,
        calibration_date="2024-01-01T00:00:00Z",
        job_id="perf",
        status="successful",
        result={"memory": [["0x0", "0x3"] * (SHOTS // 2)] * num_circuits},
    )
    return Job(
        backend=backend,
        job_id="perf",
        headers=[CircuitHeader.from_circuit(circuit) for circuit in circuits],
        shots=SHOTS,
        status=JobStatus.DONE,
        remote_data=remote_data,
    )


def _record_calls_and_memory(benchmark, api, action: Callable[[], object]) -> None:
    """Runs the action once, recording the HTTP calls it made and its peak memory"""
    calls_before = len(api.calls)
    tracemalloc.start()
    try:
        action()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    benchmark.extra_info["http_calls"] = len(api.calls) - calls_before
    benchmark.extra_info["peak_memory_bytes"] = peak
