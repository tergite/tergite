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
import json
from collections import Counter
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import requests
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus
from qiskit.qobj import PulseQobj, QasmQobj
from qiskit.result import Result
from qiskit.result.models import ExperimentResult, ExperimentResultData

from .config import REST_API_MAP
from .serialization import IQXJsonEncoder, iqx_rle

STATUS_MAP = {
    "REGISTERING": JobStatus.QUEUED,
    "DONE": JobStatus.DONE,
    # TODO: unimplemented status codes
    "INITIALIZING": JobStatus.INITIALIZING,
    "VALIDATING": JobStatus.VALIDATING,
    "RUNNING": JobStatus.RUNNING,
    "CANCELLED": JobStatus.CANCELLED,
    "ERROR": JobStatus.ERROR,
}


class Job(JobV1):
    def __init__(self: object, *, backend: object, job_id: str, upload_url: str):
        super().__init__(backend=backend, job_id=job_id, upload_url=upload_url)

    def status(self) -> JobStatus:
        jobs_url = self.backend().base_url + REST_API_MAP["jobs"]
        job_id = self.job_id()
        response = requests.get(jobs_url + "/" + job_id)
        if response.ok:
            return STATUS_MAP[response.json()["status"]]
        else:
            raise RuntimeError(f"Failed to GET status of job: {job_id}")

    def submit(self: object, payload: object, /):
        self.metadata["shots"] = payload.config.shots
        self.metadata["qobj_id"] = payload.qobj_id
        self.metadata["num_experiments"] = len(payload.experiments)
        self.payload = payload  # save input data inside job

        job_id = self.job_id()
        job_entry = {
            "job_id": job_id,
            "type": "script",  # ?
        }
        if type(payload) is QasmQobj:
            job_entry["name"] = "qasm_dummy_job"
            job_entry.update(
                {
                    "name": "qasm_dummy_job",
                    "params": {"qobj": payload.to_dict()},
                    "post_processing": "process_qiskit_qasm_runner_qasm_dummy_job",
                }
            )

        elif type(payload) is PulseQobj:
            payload = payload.to_dict()
            # In-place RLE pulse library for compression
            for pulse in payload["config"]["pulse_library"]:
                pulse["samples"] = iqx_rle(pulse["samples"])

            job_entry.update(
                {
                    "name": "pulse_schedule",
                    "params": {"qobj": payload},
                }
            )

        else:
            raise RuntimeError(f"Unprocessable payload type: {type(payload)}")

        # Serialize the job to json
        job_file = Path(gettempdir()) / str(uuid4())
        with job_file.open("w") as dest:
            json.dump(job_entry, dest, cls=IQXJsonEncoder, indent="\t")

        job_upload_url = self.metadata["upload_url"]

        # Transmit the job POST request
        with job_file.open("r") as src:
            files = {"upload_file": src}
            response = requests.post(job_upload_url, files=files)
            if not response.ok:
                raise RuntimeError(f"Failed to POST job: {job_id}")

        # Delete temporary transmission file
        job_file.unlink()
        return response

    @property
    def download_url(self) -> str:
        if self.status() != JobStatus.DONE:
            print(f"Job {self.job_id()} has not yet completed.")
            return
        jobs_url = self.backend().base_url + REST_API_MAP["jobs"]
        job_id = self.job_id()
        response = requests.get(jobs_url + "/" + job_id)
        if response.ok:
            return response.json()["download_url"]
        else:
            raise RuntimeError(f"Failed to GET download URL of job: {job_id}")

    @property
    def logfile(self) -> Path:
        url = self.download_url
        if not url:
            return
        response = requests.get(url)
        if response.ok:
            job_file = Path(gettempdir()) / (self.job_id() + ".hdf5")
            with open(job_file, "wb") as dest:
                dest.write(response.content)
            return job_file
        else:
            raise RuntimeError(f"Failed to GET logfile of job: {job_id}")

    def cancel(self):
        print("Job.cancel() is not implemented.")
        pass  # TODO: This can be implemented server side with stoppable threads.

    def result(self):
        if self.status() != JobStatus.DONE:
            print(f"Job {self.job_id()} has not yet completed.")
            return
        backend = self.backend()
        job_id = self.job_id()
        jobs_url = backend.base_url + REST_API_MAP["jobs"]
        response = requests.get(jobs_url + "/" + job_id)
        if response.ok:
            memory = response.json()["result"]["memory"]
        else:
            raise RuntimeError(f"Failed to GET memory of job: {job_id}")

        # Sanity check
        if not len(memory) == self.metadata["num_experiments"]:
            print(
                "There is a mismatch between number of experiments in the Qobj \
                and number of results recieved!"
            )
        else:
            print("Results OK")

        # Extract results
        experiment_results = list()
        for index, experiment_memory in enumerate(memory):
            experiment_results.append(
                ExperimentResult(
                    header=self.payload.experiments[index].header,
                    shots=self.metadata["shots"],
                    success=True,
                    data=ExperimentResultData(
                        counts=dict(Counter(experiment_memory)),
                        memory=experiment_memory,
                    ),
                )
            )

        return Result(
            backend_name=backend.name,
            backend_version=backend.backend_version,
            qobj_id=self.metadata["qobj_id"],
            job_id=job_id,
            success=True,
            results=experiment_results,
        )
