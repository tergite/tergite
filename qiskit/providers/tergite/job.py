# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
from qiskit.providers import JobV1, JobStatus
from qiskit.result import Result
from qiskit.qobj import PulseQobj, QasmQobj
from collections import Counter
import requests
from .config import REST_API_MAP
from pathlib import Path
from tempfile import gettempdir

class Job(JobV1):
    def __init__(self, backend, job_id: str, qobj):
        super().__init__(backend=backend, job_id=job_id)

        if qobj["type"] == "PULSE":
            self._qobj = PulseQobj.from_dict(qobj)
        else:
            self._qobj = QasmQobj.from_dict(qobj)

        self._backend = backend
        self._result = None

    @property
    def status(self):
        JOBS_URL = self._backend.base_url + REST_API_MAP["jobs"]
        job_id = self.job_id()
        response = requests.get(JOBS_URL + "/" + job_id)
        response_data = response.json()
        if response_data:
            return response_data["status"]

    def store_data(self, documents : list):
        download_url = self.download_url
        if not download_url:
            return
        CALIBS_URL = self._backend.base_url + REST_API_MAP["calibrations"]
        for doc in documents:
            doc.update({
                "job_id" :  self.job_id(),
                "download_url" : download_url
            })
        response = requests.post(CALIBS_URL, json = documents)
        if not response:
            print(f"Failed to store {len(documents)} document(s), server error: {response}")

    def submit(self,*args, **kwargs):
        print("Tergite: Job submit() is deprecated")
        pass

    @property
    def download_url(self) -> str:
        if self.status != "DONE":
            print(f"Job {self.job_id()} has not yet completed.")
            return

        JOBS_URL = self._backend.base_url + REST_API_MAP["jobs"]
        job_id = self.job_id()
        response = requests.get(JOBS_URL + "/" + job_id)
        response_data = response.json()
        if response_data:
            return response_data["download_url"]

    @property
    def logfile(self) -> Path:
        url = self.download_url
        if not url:
            return

        response = requests.get(url)
        job_file = Path(gettempdir()) / job_id
        with open(job_file, "wb") as dest:
            dest.write(response.content)
        return job_file

    def cancel(self):
        print(NotImplemented)
        pass # TODO

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

            qobj = self._qobj
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
                    "backend_name": self._backend.name,
                    "backend_version": self._backend.version,
                    "qobj_id": qobj.qobj_id,
                    "job_id": self.job_id(),
                    "success": True,
                }
            )

        return self._result
