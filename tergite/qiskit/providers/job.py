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
#
# This code was refactored from the original on 22nd September, 2023 by Martin Ahindura
"""Defines the asynchronous job that executes the experiments."""
import json
import logging
from collections import Counter
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING, Optional, Tuple, Union
from uuid import uuid4

import requests
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus
from qiskit.result import Result
from qiskit.result.models import ExperimentResult, ExperimentResultData
from requests import Response

from tergite.qiskit.deprecated.qobj import PulseQobj, QasmQobj

from .config import REST_API_MAP
from .serialization import IQXJsonEncoder, iqx_rle

if TYPE_CHECKING:
    from tergite.qiskit.providers.tergite import Provider

    from .backend import TergiteBackend

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
    """A representation of the asynchronous job that handles experiments on a backend"""

    def __init__(self, *, backend: "TergiteBackend", job_id: str, upload_url: str):
        """Initializes the job instance for the given backend

        Args:
            backend: the backed where the job is to run
            job_id: the unique id of the job
            upload_url: URL where the jobs will be uploaded
        """
        super().__init__(backend=backend, job_id=job_id, upload_url=upload_url)
        self.payload: Optional[Union[QasmQobj, PulseQobj]] = None

    def status(self) -> JobStatus:
        response = self._get_job_results()
        if response.ok:
            return STATUS_MAP[response.json()["status"]]
        else:
            raise RuntimeError(f"Failed to GET status of job: {self.job_id()}")

    def submit(self, payload: Union[QasmQobj, PulseQobj], /) -> requests.Response:
        """Submit the job to the backend for execution.

        Args:
            payload: the QasmQobj or PulseQobj object to execute

        Returns:
            requests.Response: the response of the API after submitting the job
        """
        self.metadata["shots"] = payload.config.shots
        self.metadata["qobj_id"] = payload.qobj_id
        self.metadata["num_experiments"] = len(payload.experiments)
        self.payload = payload  # save input data inside job

        job_id = self.job_id()
        job_entry = {
            "job_id": job_id,
            "type": "script",  # ?
        }
        if isinstance(payload, QasmQobj):
            job_entry["name"] = "qasm_dummy_job"
            job_entry.update(
                {
                    "name": "qasm_dummy_job",
                    "params": {"qobj": payload.to_dict()},
                    "post_processing": "process_qiskit_qasm_runner_qasm_dummy_job",
                }
            )
        elif isinstance(payload, PulseQobj):
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

        backend: "TergiteBackend" = self.backend()
        provider: "Provider" = backend.provider
        auth_headers = provider.get_auth_headers()

        # Transmit the job POST request
        with job_file.open("r") as src:
            files = {"upload_file": src}
            response = requests.post(job_upload_url, files=files, headers=auth_headers)
            if not response.ok:
                raise RuntimeError(f"Failed to POST job: {job_id}")

        # Delete temporary transmission file
        job_file.unlink()
        return response

    @property
    def download_url(self) -> Optional[str]:
        """The download_url of this job when it is completed"""
        if self.status() != JobStatus.DONE:
            print(f"Job {self.job_id()} has not yet completed.")
            return

        response = self._get_job_results()
        if response.ok:
            return response.json()["download_url"]
        else:
            raise RuntimeError(f"Failed to GET download URL of job: {self.job_id()}")

    @property
    def logfile(self) -> Optional[Path]:
        """The path to the logfile of this job when it is completed"""
        url = self.download_url
        if not url:
            return

        backend: "TergiteBackend" = self.backend()
        provider: "Provider" = backend.provider
        auth_headers = provider.get_auth_headers()

        response = requests.get(url, headers=auth_headers)
        job_id = self.job_id()
        if response.ok:
            job_file = Path(gettempdir()) / (job_id + ".hdf5")
            with open(job_file, "wb") as dest:
                dest.write(response.content)
            return job_file
        else:
            raise RuntimeError(f"Failed to GET logfile of job: {job_id}")

    def cancel(self):
        print("Job.cancel() is not implemented.")
        pass  # TODO: This can be implemented server side with stoppable threads.

    def result(self) -> Optional[Result]:
        """Retrieves the outcome of this job when it is completed.

        It returns None if the job has not yet completed

        Returns:
            Optional[qiskit.result.result.Result]: the outcome of this job
                if it has completed
        """
        if self.status() != JobStatus.DONE:
            print(f"Job {self.job_id()} has not yet completed.")
            return

        response = self._get_job_results()
        if response.ok:
            memory = response.json()["result"]["memory"]
        else:
            raise RuntimeError(f"Failed to GET memory of job: {self.job_id()}")

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

        backend = self.backend()
        return Result(
            backend_name=backend.name,
            backend_version=backend.backend_version,
            qobj_id=self.metadata["qobj_id"],
            job_id=self.job_id(),
            success=True,
            results=experiment_results,
        )

    def _get_job_results(self) -> Response:
        """Retrieves the results of this job from the backend"""
        backend: "TergiteBackend" = self.backend()
        provider: "Provider" = backend.provider
        url = f"{backend.base_url}{REST_API_MAP['jobs']}/{self.job_id()}"
        auth_headers = provider.get_auth_headers()
        return requests.get(url, headers=auth_headers)

    def __repr__(self):
        kwargs = [f"{k}={repr(v)}" for k, v in self.__dict__.items()]
        kwargs_str = ",\n".join(kwargs)
        return f"{self.__class__.__name__}({kwargs_str})"

    def __eq__(self, other):
        if not isinstance(other, Job):
            return False

        for k, v in self.__dict__.items():
            other_v = getattr(other, k, None)
            if other_v != v:
                diff = {"expected": {k: other_v}, "got": {k: v}}
                logging.error(f"Job differs: {diff}")
                return False

        return True
