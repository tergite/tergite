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

from tergite_qiskit_connector.providers.tergite import Tergite, Job
from tergite_qiskit_connector.providers.tergite.provider_account import ProviderAccount

if __name__ == "__main__":
    # the Tergite API URL e.g. "https://api.tergite.example"
    API_URL = "https://api.qal9000.se"
    # API token for connecting to tergite. Required if no username/password
    API_TOKEN = "<your Tergite API key >"
    # API username, required if API_TOKEN is not set.
    API_USERNAME = None  # "<your API username>"
    # API password, required if API_USERNAME is set
    API_PASSWORD = "<your API password>"
    # The name of the Quantum Computer to use from the available quantum computers
    BACKEND_NAME = "SimulatorC"
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
    if API_USERNAME:
        account_extras = {"username": API_USERNAME, "password": API_PASSWORD}
    else:
        account_extras = {}

    # provider account creation can be skipped in case you already saved
    # your provider account to the `~/.qiskit/tergiterc` file.
    # See below how that is done.
    account = ProviderAccount(
        service_name=SERVICE_NAME, url=API_URL, token=API_TOKEN, extras=account_extras
    )
    provider = Tergite.use_provider_account(account)
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

    # view the results
    elapsed_time = 0
    result = None
    while result is None:
        if elapsed_time > POLL_TIMEOUT:
            raise TimeoutError(f"result polling timeout {POLL_TIMEOUT} seconds exceeded")

        time.sleep(1)
        elapsed_time += 1
        result = job.result()

    print(result.get_counts())
