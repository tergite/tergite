# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
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
import requests
from .config import REST_API_MAP
from pathlib import Path


class Job(BaseJob):
    def __init__(self, backend, job_id: str, qobj):
        super().__init__(backend, job_id)
        self._qobj = qobj
        self._backend = backend
        self._status = JobStatus.INITIALIZING
        self._result = None
        self._download_url = None

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
            JOBS_URL = self._backend.base_url + REST_API_MAP["jobs"]
            job_id = self.job_id()
            response = requests.get(JOBS_URL + "/" + job_id + REST_API_MAP["result"])

            if response:
                self._response = response  # store response for debugging
                memory = response.json()["memory"]
            else:
                return self._result

            # Note: We currently measure all qubits and ignore classical registers.

            qobj = self.qobj()
            experiment_results = []

            if not len(memory) == len(qobj.experiments):
                print(
                    "There is a mismatch between number of experiments in the Qobj \
                    and number of results recieved!"
                )
            else:
                print("Results OK")

            for index, experiment_memory in enumerate(memory):
                data = {
                    "counts": dict(Counter(experiment_memory)),
                    "memory": experiment_memory,
                }

                # Note: Filling in details from qobj is only to make Qiskit happy
                # In future, much of this information should be provided by MSS
                experiment_results.append(
                    {
                        "name": qobj.experiments[index].header.name,
                        "success": True,
                        "shots": qobj.config.shots,
                        "data": data,
                        "header": qobj.experiments[index].header.to_dict(),
                    }
                )

                experiment_results[index]["header"][
                    "memory_slots"
                ] = self._backend.configuration().n_qubits

            # Note: Filling in details from qobj is only to make Qiskit happy
            # In future, much of this information should be provided by MSS
            self._result = Result.from_dict(
                {
                    "results": experiment_results,
                    "backend_name": self._backend.name(),
                    "backend_version": self._backend.version(),
                    "qobj_id": qobj.qobj_id,
                    "job_id": self.job_id(),
                    "success": True,
                }
            )

        return self._result

    # NOTE: This API is WIP
    def download_logfile(self, save_location: str):
        # TODO: improve error handling
        if not self._download_url:
            JOBS_URL = self._backend.base_url + REST_API_MAP["jobs"]
            job_id = self.job_id()
            response = requests.get(
                JOBS_URL + "/" + job_id + REST_API_MAP["download_url"]
            )
            print(response.json())

            if response:
                self._response = response  # for debugging
                self._download_url = response.json()
            else:
                return None

        response = requests.get(self._download_url)
        if response:
            file = Path(save_location) / (self.job_id() + ".hdf5")
            with file.open("wb") as destination:
                destination.write(response.content)

        return None

    def submit(self):
        print("Tergite: Job submit() is deprecated")
        return None
