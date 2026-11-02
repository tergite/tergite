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
"""End-to-end tests for a job's life after it is submitted"""
import os

import h5py
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.providers import JobStatus

from tergite import Provider, Tergite
from tergite.exc import JobFailedError


def test_job_reaches_done(backend_provider: Provider):
    """A submitted job's status ends at DONE, with a result"""
    job = _run_x(backend_provider)
    job.wait_for_final_state(timeout=300)

    assert job.status() == JobStatus.DONE
    assert sum(job.result().get_counts().values()) == 100


def test_provider_job_from_a_new_provider(backend_provider: Provider):
    """provider.job(job_id) on a provider of its own returns the job and its result"""
    job = _run_x(backend_provider)
    job.wait_for_final_state(timeout=300)
    other_provider = Tergite.use_provider_account(
        service_name="other", url=os.environ["API_URL"], token=os.environ["API_TOKEN"]
    )

    got = other_provider.job(job.job_id())

    assert got.status() == JobStatus.DONE
    assert got.result().get_counts() == job.result().get_counts()


def test_logfile_downloads(backend_provider: Provider):
    """job.logfile is the job's HDF5 logfile, downloaded"""
    job = _run_x(backend_provider)
    job.wait_for_final_state(timeout=300)

    with h5py.File(job.logfile, "r") as logfile:
        assert "header" in logfile


def test_cancelled_job_result_raises(backend_provider: Provider):
    """A job cancelled before it ran raises JobFailedError from result(); one that ran first has counts"""
    job = _run_x(backend_provider)
    job.cancel()
    job.wait_for_final_state(timeout=300)

    if job.status() == JobStatus.CANCELLED:
        with pytest.raises(JobFailedError, match="was cancelled"):
            job.result()
    else:
        assert job.status() == JobStatus.DONE


def _run_x(provider: Provider):
    """Runs an X gate on qubit 0 of the one-qubit simulator, measured, for 100 shots"""
    backend = provider.get_backend("qiskit_pulse_1q")
    backend.set_options(shots=100)
    qc = QuantumCircuit(1, 1)
    qc.x(0)
    qc.measure(0, 0)
    return backend.run(transpile(qc, backend=backend), meas_level=2)
