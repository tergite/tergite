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
import uuid
from collections import Counter

import numpy as np
from qiskit import QuantumCircuit, circuit, compiler, pulse
from qiskit.pulse.transforms import AlignLeft
from qiskit.result import Result
from qiskit.result.models import ExperimentResult, ExperimentResultData

from tergite_qiskit_connector.providers.tergite import Job, OpenPulseBackend, Tergite
from tergite_qiskit_connector.providers.tergite.backend import TergiteBackendConfig
from tergite_qiskit_connector.providers.tergite.provider_account import ProviderAccount
from tests.conftest import (
    API_URL,
    BACKENDS_LIST,
    GOOD_BACKEND,
    NUMBER_OF_SHOTS,
    QUANTUM_COMPUTER_URL,
    TEST_JOB_ID,
    TEST_JOB_RESULTS,
)
from tests.utils.records import get_record


def test_transpile(api):
    """compiler.transpile(qc, backend=backend) returns backend-specific QuantumCircuits"""
    backend = _get_backend()
    qc = _get_test_qiskit_circuit()
    expected = _get_expected_transpiled_circuit()
    got = compiler.transpile(qc, backend=backend)
    assert got == expected


def test_run(api):
    """backend.run(tc, meas_level=2) returns a registered job"""
    backend = _get_backend()
    backend.set_options(shots=NUMBER_OF_SHOTS)
    tc = _get_expected_transpiled_circuit()
    qobj_id = str(uuid.uuid4())
    expected = _get_expected_job(
        backend=backend, transpiled_circuit=tc, meas_level=2, qobj_id=qobj_id
    )
    got = backend.run(tc, meas_level=2, qobj_id=qobj_id)
    assert got == expected


def test_job_result(api):
    """job.result() returns a successful job's results"""
    backend = _get_backend()
    tc = _get_expected_transpiled_circuit()
    job = backend.run(tc, meas_level=2)

    expected = _get_expected_job_result(backend=backend, job=job)
    got = job.result()
    assert got.to_dict() == expected.to_dict()


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
    **options
) -> Job:
    """Returns the expected job after being initialized"""
    schedule = compiler.schedule(transpiled_circuit, backend=backend)
    qobj = compiler.assemble(
        experiments=[schedule],
        backend=backend,
        shots=NUMBER_OF_SHOTS,
        qubit_lo_freq=backend.qubit_lo_freq,
        meas_lo_freq=backend.meas_lo_freq,
        qobj_id=qobj_id,
        **options
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
    rx_block.append(pulse.SetFrequency(3304746060, pulse.DriveChannel(1)))
    rx_block.append(
        pulse.Play(
            pulse.Gaussian(duration=52, amp=(0.03308 + 0j), sigma=6, name="RX q1"),
            pulse.DriveChannel(1),
            name="RX q1",
        )
    )

    qc._calibrations = {
        "rz": {((1,), (phase,)): rz_block},
        "rx": {((1,), (phase,)): rx_block},
    }

    return qc


def _get_backend():
    """Retrieves the right backend"""
    account = ProviderAccount(service_name="test", url=API_URL)
    provider = Tergite.use_provider_account(account)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": GOOD_BACKEND})
    return OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )
