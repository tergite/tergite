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
# Alteration Notice
# -----------------
# This code was refactored from the original by:
#
# Martin Ahindura, 2023
"""Defines the asynchronous job that executes the experiments."""
import logging
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JOB_FINAL_STATES, JobStatus
from qiskit.result import Result
from qiskit.result.models import ExperimentResult, ExperimentResultData

from ..compat.qiskit.qobj import PulseQobj
from ..services import api_client as client
from ..services.api_client import JobFile
from ..services.api_client.dtos import RemoteJobStatus

# from ..services.api_client.dtos import RemoteJobStatus
from ..utils.qobj import compress_qobj_dict

if TYPE_CHECKING:
    from .backend import TergiteBackend
    from .provider import Provider

_JOB_FINAL_OR_INITIAL_STATES = (*JOB_FINAL_STATES, JobStatus.INITIALIZING)


class Job(JobV1):
    """A representation of the asynchronous job that handles experiments on a backend"""

    def __init__(
        self,
        *,
        backend: "TergiteBackend",
        job_id: str,
        payload: Optional[PulseQobj] = None,
        upload_url: Optional[str] = None,
        remote_data: Optional["client.RemoteJob"] = None,
        logfile: Optional[Path] = None,
        status: JobStatus = JobStatus.INITIALIZING,
        download_url: Optional[str] = None,
        calibration_date: Optional[str] = None,
        access_token: Optional[str] = None,
        **kwargs,
    ):
        """Initializes the job instance for the given backend

        Args:
            backend: the backed where the job is to run
            job_id: the unique id of the job
            upload_url: URL where the jobs will be uploaded
            payload: the qobj representing the experiments
            remote_data: the job data from the remote API
            logfile: the HDF5 logfile for this job
            status: the JobStatus of the current job; defaults to `JobStatus.INITIALIZING`
            download_url: the URL to download the results logfile from
            calibration_date: the last_calibrated timestamp of the backend when this job was compiled
            access_token: the access token for submitting jobs to BCC
            kwargs: extra key-word arguments to add to the job's metadata
        """
        super().__init__(
            backend=backend, job_id=job_id, upload_url=upload_url, **kwargs
        )
        self.payload = payload
        self.upload_url = upload_url
        self._status = status
        self._logfile = logfile
        self._provider: Provider = backend.provider
        self._download_url = download_url
        self._calibration_date = calibration_date
        self._result: Optional[Result] = None
        self._remote_data = remote_data
        self._account = backend.provider.account
        self._access_token = access_token

    @property
    def _is_in_final_state(self):
        """Whether this job has reached the end of the line or not

        It returns True if the job status is in `CANCELLED`, `ERROR`, `DONE`
        """
        try:
            return self._status in JOB_FINAL_STATES
        except RuntimeError:
            return False

    @property
    def remote_data(self) -> Optional["client.RemoteJob"]:
        """The representation of the job in the remote API"""
        if not self._is_in_final_state:
            self._remote_data = client.get_remote_job_data(self._account, self.job_id())

        return self._remote_data

    def status(self) -> JobStatus:
        if not self._is_in_final_state:
            try:
                self._status = STATUS_MAP[self.remote_data.status]
            except (KeyError, AttributeError):
                pass

        return self._status

    def submit(self) -> requests.Response:
        """Submit the job to the backend for execution.

        Returns:
            requests.Response: the response of the API after submitting the job
        """
        if self._status != JobStatus.INITIALIZING:
            raise ValueError("This job was already submitted")

        if self.upload_url is None:
            raise ValueError("This job is not submittable. It lacks an upload_url")

        if not isinstance(self.payload, PulseQobj):
            raise RuntimeError(f"Unprocessable payload type: {type(self.payload)}")

        if self._access_token is None:
            raise ValueError("This job is not submittable. It lacks an access token")

        payload = compress_qobj_dict(self.payload.to_dict())
        job_entry = JobFile.model_validate(
            {
                "job_id": self.job_id(),
                "params": {"qobj": payload},
            }
        )

        return client.send_job_file(
            self._account,
            url=self.upload_url,
            job_data=job_entry,
            access_token=self._access_token,
        )

    @property
    def download_url(self) -> Optional[str]:
        """The download_url of this job when it is completed

        Raises:
            RuntimeError: Failed to GET download URL of job: {job_id}. Status: {JobStatus}
        """
        if self._download_url is None and self.status() in JOB_FINAL_STATES:
            try:
                self._download_url = self.remote_data.download_url
            except KeyError:
                raise RuntimeError(
                    f"Failed to GET download URL of job: {self.job_id()}. Status: {self.status()}"
                )

        return self._download_url

    @property
    def logfile(self) -> Optional[Path]:
        """The path to the logfile of this job when it is completed"""
        if self._logfile is None and self.status() in JOB_FINAL_STATES:
            if self.download_url:
                self._logfile = client.download_job_logfile(
                    self.job_id(),
                    url=self.download_url,
                    access_token=self._access_token,
                )

        return self._logfile

    def cancel(self):
        """Attempt to cancel the job.

        Raises:
            ValueError: This job is not cancellable. It lacks an upload_url
            RuntimeError: Failed to cancel job '{job_id}': {detail}
        """
        if self.upload_url is None:
            raise ValueError("This job is not cancellable. It lacks an upload_url")

        client.cancel_job(
            upload_url=self.upload_url,
            job_id=self.job_id(),
            access_token=self._access_token,
        )

    def result(self) -> Optional[Result]:
        """Retrieves the outcome of this job when it is completed.

        It returns None if the job has not yet completed

        Returns:
            Optional[qiskit.result.result.Result]: the outcome of this job
                if it has completed

        Raises:
            RuntimeError: failed to GET memory of job: {job_id}
            RuntimeError: unexpected number of results; expected {num}, got: {num}
        """
        status = self.status()
        if status not in JOB_FINAL_STATES:
            logging.info(f"Job {self.job_id()} is not DONE. Status: {status}.")
            return

        if self._result is None:
            backend: TergiteBackend = self.backend()
            n_qubits = self.payload.config.n_qubits

            try:
                memory = self.remote_data.result.memory
            except AttributeError:
                raise RuntimeError(f"failed to GET memory of job: {self.job_id()}")

            # Sanity check
            if len(memory) != len(self.payload.experiments):
                raise RuntimeError(
                    f"unexpected number of results;"
                    f"expected {len(self.payload.experiments)}, got: {len(memory)}"
                )
            meas_level = self.payload.config.meas_level
            has_counts = meas_level == 2

            # FIXME: There is an assumption that classical register length is equal to n_qubits
            # Instead we should catch classical register size before we convert circuit to schedule and save it
            for exp in self.payload.experiments:
                # headers are dataclasses; set attribute directly
                setattr(exp.header, "memory_slots", n_qubits)

            self._result = Result(
                backend_name=backend.name,
                backend_version=backend.backend_version,
                qobj_id=self.payload.qobj_id,
                job_id=self.job_id(),
                success=True,
                results=[
                    ExperimentResult(
                        header=self.payload.experiments[idx].header,
                        shots=self.payload.config.shots,
                        success=True,
                        meas_level=meas_level,
                        data=ExperimentResultData(
                            counts=dict(Counter(v)) if has_counts else None,
                            memory=v,
                        ),
                    )
                    for idx, v in enumerate(memory)
                ],
            )

        return self._result

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
                return False

        return True


STATUS_MAP = {
    RemoteJobStatus.PENDING: JobStatus.QUEUED,
    RemoteJobStatus.SUCCESSFUL: JobStatus.DONE,
    RemoteJobStatus.EXECUTING: JobStatus.RUNNING,
    RemoteJobStatus.CANCELLED: JobStatus.CANCELLED,
    RemoteJobStatus.FAILED: JobStatus.ERROR,
}
