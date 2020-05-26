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


class Job(BaseJob):
    def __init__(self, backend, job_id, qobj):
        super().__init__(backend, job_id)
        self._qobj = qobj
        self._backend = backend
        self._status = JobStatus.INITIALIZING

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
        print("Tergite: Job result() not implemented yet")
        return None

    def submit(self):
        print("Tergite: Job submit() is deprecated")
        return None
