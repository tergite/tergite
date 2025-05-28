# This code is part of Tergite
#
# (C) Copyright Axel Andersson 2022
# (C) Copyright Stefan Hill 2023
# (C) Copyright Martin Ahindura 2023, 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
#
# This code was refactored from the original on 22nd September, 2023 by Martin Ahindura
"""A sample script doing a very simple quantum operation"""
import time

import qiskit.circuit as circuit
import qiskit.compiler as compiler

from tergite import Job, Tergite

if __name__ == "__main__":
    # the Tergite API URL e.g. "https://api.tergite.example"
    API_URL = "https://api.qal9000.se"
    # API token for connecting to tergite
    API_TOKEN = "<your Tergite API key >"
    # The name of the Quantum Computer to use from the available quantum computers
    BACKEND_NAME = "qiskit_pulse_2q"
    # the name of this service. For your own bookkeeping.
    SERVICE_NAME = "local"
    # the timeout in seconds for how long to keep checking for results
    POLL_TIMEOUT = 100

    # create the Qiskit circuit
    qc = circuit.QuantumCircuit(1)
    qc.x(0)
    qc.h(0)
    qc.measure_all()

    # create a provider
    # provider account creation can be skipped in case you already saved
    # your provider account to the `~/.qiskit/tergiterc` file.
    # See below how that is done.
    provider = Tergite.use_provider_account(
        service_name=SERVICE_NAME, url=API_URL, token=API_TOKEN
    )
    # to save this account to the `~/.qiskit/tergiterc` file, add the `save=True`
    # provider = Tergite.use_provider_account(account, save=True)

    # Get the tergite backend in case you skipped provider account creation
    # provider = Tergite.get_provider(service_name=SERVICE_NAME)
    backend = provider.get_backend(BACKEND_NAME)
    backend.set_options(shots=1024)

    # compile the circuit
    tc = compiler.transpile(qc, backend=backend)

    # run the circuit
    job: Job = backend.run(tc, meas_level=2, meas_return="single")
    job.wait_for_final_state(timeout=POLL_TIMEOUT)
    result = job.result()

    print(result.get_counts())
