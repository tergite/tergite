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


# this file is meant to be run interactively for objects inspection
# python -i tests/job_on_simulator.py

from qiskit import *

backend = BasicAer.get_backend("qasm_simulator")

circ = QuantumCircuit(3, 3)

circ.x(2)
circ.h(1)
circ.measure([0, 1, 2], [0, 1, 2])

job = execute(circ, backend)
counts = job.result().get_counts()

print("Counts:", counts)
# plot_histogram(counts).show()
