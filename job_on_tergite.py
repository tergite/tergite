# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
import logging

# this file is meant to be run interactively for objects inspection
# python -i tests/job_on_tergite.py

from time import sleep

import qiskit
from qiskit.compiler import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.providers.tergite import Tergite

if __name__ == '__main__':

    provider = Tergite.get_provider()
    backend = provider.get_backend("loke_system_test")
    backend.set_options(shots=1024)
    # backend = qiskit.Aer.get_backend('aer_simulator')

    qc = QuantumCircuit(1)
    qc.x(0)
    qc.h(0)
    qc.measure_all()
    # qc.delay(300_000)

    t_circuit = transpile(qc, backend)

    job = backend.run(t_circuit, meas_level=2, meas_return='single')

    for i in range(100):
        try:
            print(job.result().get_counts())
            break
        except:
            sleep(1)
            logging.warning('Cannot retrieve job result')
