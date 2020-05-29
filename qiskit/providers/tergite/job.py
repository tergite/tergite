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

from qiskit.providers import BaseJob, JobStatus
from qiskit.result import Result
from collections import Counter


class Job(BaseJob):
    def __init__(self, backend, job_id, qobj):
        super().__init__(backend, job_id)
        self._qobj = qobj
        self._backend = backend
        self._status = JobStatus.INITIALIZING
        self._result = None

    def qobj(self):
        return self._qobj

    def backend(self):
        return self._backend

    def status(self):
        print("Tergite: Job status() not implemented yet")
        return self._status

    def cancel(self):
        print("Tergite: Job cancel() not implemented yet")
        return None

    def result(self):
        if not self._result:
            # test values
            # next step is to fetch data from MSS
            print("Tergite: Simulated results")
            memory = ["0x0", "0x1", "0x2", "0x2"]

            data = {"counts": dict(Counter(memory)), "memory": memory}

            qobj = self.qobj()

            experiment_results = []
            experiment_results.append(
                {
                    "name": qobj.experiments[0].header.name,
                    "success": True,
                    "shots": qobj.config.shots,
                    "data": data,
                    "header": qobj.experiments[0].header.to_dict(),
                }
            )

            # we currently measure all qubits and ignore classical registers
            experiment_results[0]["header"][
                "memory_slots"
            ] = self._backend.configuration().n_qubits

            self._result = Result.from_dict(
                {
                    "results": experiment_results,
                    "backend_name": self._backend.name(),
                    "backend_version": self._backend.version(),
                    "qobj_id": 0,
                    "job_id": self.job_id(),
                    "success": True,
                }
            )

        return self._result

    def submit(self):
        print("Tergite: Job submit() is deprecated")
        return None
