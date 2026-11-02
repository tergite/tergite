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
"""The round trip of jobs from run() to result() against the native e2e stack.

dev/perf/record.sh runs it through dev/e2e_native_test.sh, which starts the stack and passes
the process IDs of MSS and the backends. It writes roundtrip.json into PERF_DIR: per kind of
job, its latencies, throughput, HTTP calls and bytes uploaded; per process, its CPU time and
peak memory, children included.
"""
import json
import os
import statistics
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List

import httpx
import psutil
import pytest
from qiskit import QuantumCircuit, transpile

from tergite import Provider, Tergite
from tests.utils.jobs import wait_for_final_state

JOBS_PER_KIND = 5
SAMPLE_SECONDS = 0.2
# name: (backend, qubits, meas_level, meas_return)
JOB_KINDS = {
    "1q_counts": ("qiskit_pulse_1q", 1, 2, "single"),
    "2q_counts": ("qiskit_pulse_2q", 2, 2, "single"),
    "2q_iq": ("qiskit_pulse_2q", 2, 1, "single"),
    "loke_counts": ("Loke", 1, 2, "single"),
}
PROCESS_ENV_VARS = {
    "mss": "MSS_PID",
    "simulators": "SIMULATORS_PID",
    "loke": "LOKE_PID",
}


def test_roundtrip(http_log: List[httpx.Request]):
    """Runs each kind of job several times, recording what the round trip costs"""
    provider = Tergite.use_provider_account(
        service_name="perf", url=os.environ["API_URL"], token=os.environ["API_TOKEN"]
    )
    with _sample_processes() as process_stats:
        kinds = {
            name: _measure_kind(provider, http_log, *params)
            for name, params in JOB_KINDS.items()
        }

    output = Path(os.environ["PERF_DIR"]) / "roundtrip.json"
    output.write_text(
        json.dumps({"kinds": kinds, "processes": process_stats}, indent=2) + "\n"
    )


@pytest.fixture
def http_log(monkeypatch) -> List[httpx.Request]:
    """The requests the SDK sends, as it sends them"""
    log = []
    send = httpx.Client.send

    def logged_send(client, request, **kwargs):
        # read so the multipart upload's size is known; its stream is in memory, so re-readable
        request.read()
        log.append(request)
        return send(client, request, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", logged_send)
    return log


def _measure_kind(
    provider: Provider,
    http_log: List[httpx.Request],
    backend_name: str,
    num_qubits: int,
    meas_level: int,
    meas_return: str,
) -> Dict[str, float]:
    """Runs the kind of job JOBS_PER_KIND times, one after another, measuring each"""
    backend = provider.get_backend(backend_name)
    backend.set_options(shots=100)
    qc = QuantumCircuit(num_qubits, num_qubits)
    qc.x(0)
    qc.measure(range(num_qubits), range(num_qubits))
    circuit = transpile(qc, backend=backend)

    latencies = []
    calls = 0
    upload_bytes = 0
    started = time.perf_counter()
    for _ in range(JOBS_PER_KIND):
        job_started = time.perf_counter()
        calls_before_run = len(http_log)
        job = backend.run(circuit, meas_level=meas_level, meas_return=meas_return)
        run_requests = http_log[calls_before_run:]
        # the status polls vary with timing, so the calls counted are run's and result's
        wait_for_final_state(job)
        calls_before_result = len(http_log)
        job.result()
        latencies.append(time.perf_counter() - job_started)
        calls += len(run_requests) + len(http_log) - calls_before_result
        # the upload goes to the backend's /jobs; MSS registers jobs at /jobs/
        upload_bytes += sum(
            len(r.content)
            for r in run_requests
            if r.method == "POST" and r.url.path.endswith("/jobs")
        )
    elapsed = time.perf_counter() - started

    return {
        "p50_ms": statistics.median(latencies) * 1000,
        "p95_ms": _get_p95(latencies) * 1000,
        "jobs_per_minute": JOBS_PER_KIND / elapsed * 60,
        "http_calls_per_job": calls / JOBS_PER_KIND,
        "upload_bytes_per_job": upload_bytes / JOBS_PER_KIND,
    }


def _get_p95(values: List[float]) -> float:
    """The 95th percentile of the values, the largest when there are fewer than 20"""
    return statistics.quantiles(values, n=20, method="inclusive")[-1]


@contextmanager
def _sample_processes() -> Iterator[Dict[str, Dict[str, float]]]:
    """Samples the CPU time and memory of this process, MSS and the backends while the
    block runs, each with its children; yields the stats, filled in as the block ends"""
    processes = {"sdk": psutil.Process()}
    for name, env_var in PROCESS_ENV_VARS.items():
        if os.environ.get(env_var):
            processes[name] = psutil.Process(int(os.environ[env_var]))
    stats = {name: {"cpu_seconds": 0.0, "peak_rss_mib": 0.0} for name in processes}
    cpu_at_start = {name: _get_cpu_seconds(p) for name, p in processes.items()}
    is_done = threading.Event()

    def sample() -> None:
        while not is_done.wait(SAMPLE_SECONDS):
            for name, process in processes.items():
                rss = _get_rss_mib(process)
                stats[name]["peak_rss_mib"] = max(stats[name]["peak_rss_mib"], rss)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        yield stats
    finally:
        is_done.set()
        sampler.join()
        for name, process in processes.items():
            stats[name]["cpu_seconds"] = _get_cpu_seconds(process) - cpu_at_start[name]


def _get_cpu_seconds(process: psutil.Process) -> float:
    """The user and system CPU time of the process and its children"""
    total = 0.0
    for each in [process, *process.children(recursive=True)]:
        try:
            times = each.cpu_times()
            total += times.user + times.system
        except psutil.NoSuchProcess:
            pass
    return total


def _get_rss_mib(process: psutil.Process) -> float:
    """The resident memory of the process and its children, in MiB"""
    total = 0
    for each in [process, *process.children(recursive=True)]:
        try:
            total += each.memory_info().rss
        except psutil.NoSuchProcess:
            pass
    return total / 1024**2
