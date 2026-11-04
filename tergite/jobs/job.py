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
# Chalmers Next Labs, 2026
"""The asynchronous job that runs circuits on a backend"""
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JOB_FINAL_STATES, JobStatus
from qiskit.result import Result

from ..clients.bcc.models import JobFile
from ..clients.mss import models as mss_models
from ..exc import ApiError, JobFailedError
from .results import CircuitHeader, get_result

if TYPE_CHECKING:
    from ..backends.backend import TergiteBackend

STATUS_MAP = {
    mss_models.JobStatus.pending: JobStatus.QUEUED,
    mss_models.JobStatus.successful: JobStatus.DONE,
    mss_models.JobStatus.executing: JobStatus.RUNNING,
    mss_models.JobStatus.cancelled: JobStatus.CANCELLED,
    mss_models.JobStatus.failed: JobStatus.ERROR,
}


class Job(JobV1):
    """A job of circuits on a backend, whose status and result MSS keeps"""

    def __init__(
        self,
        *,
        backend: "TergiteBackend",
        job_id: str,
        headers: Optional[List[CircuitHeader]] = None,
        shots: Optional[int] = None,
        meas_level: int = 2,
        meas_return: str = "single",
        upload_url: Optional[str] = None,
        remote_data: Optional[mss_models.Job] = None,
        logfile: Optional[Path] = None,
        status: JobStatus = JobStatus.INITIALIZING,
        download_url: Optional[str] = None,
        calibration_date: Optional[str] = None,
        access_token: Optional[str] = None,
        **kwargs: Any,
    ):
        """Initializes the job instance for the given backend

        Args:
            backend: the backend where the job is to run
            job_id: the unique id of the job
            headers: the header of each circuit, or None where they are unknown, as for a
                job got by its id
            shots: the shots of each circuit
            meas_level: 2 for counts, 1 for IQ points
            meas_return: single for each shot's, avg for their average
            upload_url: URL where the job is uploaded
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
        self.headers = headers
        self.shots = shots
        self.meas_level = meas_level
        self.meas_return = meas_return
        self.upload_url = upload_url
        self._status = status
        self._logfile = logfile
        self._provider = backend.provider
        self._download_url = download_url
        self._calibration_date = calibration_date
        self._result: Optional[Result] = None
        self._remote_data = remote_data
        self._access_token = access_token

    @property
    def remote_data(self) -> Optional[mss_models.Job]:
        """The representation of the job in the remote API"""
        if self._status not in JOB_FINAL_STATES:
            self._remote_data = self._provider.mss_client.get_job(self.job_id())
        return self._remote_data

    def status(self) -> JobStatus:
        if self._status not in JOB_FINAL_STATES:
            self._status = STATUS_MAP.get(self.remote_data.status, self._status)
        return self._status

    def submit(self, job_file: JobFile) -> None:
        """Uploads the job file to the backend, which runs it

        Args:
            job_file: the circuits, and how to run and measure them

        Raises:
            ValueError: This job was already submitted, or is not submittable
            ApiError: Failed to POST job '{job_id}': {detail}
        """
        if self._status != JobStatus.INITIALIZING:
            raise ValueError("This job was already submitted")
        if self.upload_url is None:
            raise ValueError("This job is not submittable. It lacks an upload_url")
        if self._access_token is None:
            raise ValueError("This job is not submittable. It lacks an access token")

        self._provider.bcc_client.upload_job(
            url=self.upload_url,
            job_file=job_file,
            access_token=self._access_token,
        )

    @property
    def download_url(self) -> Optional[str]:
        """The download_url of this job when it is completed"""
        if self._download_url is None and self.status() in JOB_FINAL_STATES:
            self._download_url = self.remote_data.download_url
        return self._download_url

    @property
    def logfile(self) -> Optional[Path]:
        """The path to the logfile of this job when it is completed"""
        if self._logfile is None and self.status() in JOB_FINAL_STATES:
            if self.download_url:
                self._logfile = self._provider.bcc_client.download_logfile(
                    url=self.download_url,
                    job_id=self.job_id(),
                    access_token=self._access_token,
                )
        return self._logfile

    def cancel(self) -> None:
        """Attempt to cancel the job.

        Raises:
            ValueError: This job is not cancellable. It lacks an upload_url
            ApiError: Failed to cancel job '{job_id}': {detail}
        """
        if self.upload_url is None:
            raise ValueError("This job is not cancellable. It lacks an upload_url")

        self._provider.bcc_client.cancel_job(
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
            JobFailedError: Job {job_id} failed: {failure_reason}
            JobFailedError: Job {job_id} was cancelled: {cancellation_reason}
            ApiError: failed to GET memory of job: {job_id}
            ApiError: unexpected number of results; expected {num}, got: {num}
        """
        status = self.status()
        if status not in JOB_FINAL_STATES:
            logging.info(f"Job {self.job_id()} is not DONE. Status: {status}.")
            return None

        if status == JobStatus.ERROR:
            reason = self.remote_data.failure_reason
            raise JobFailedError(f"Job {self.job_id()} failed: {reason}")

        if status == JobStatus.CANCELLED:
            reason = self.remote_data.cancellation_reason
            raise JobFailedError(f"Job {self.job_id()} was cancelled: {reason}")

        if self._result is None:
            if self.remote_data.result is None:
                raise ApiError(f"failed to GET memory of job: {self.job_id()}")
            backend = self.backend()
            self._result = get_result(
                job_id=self.job_id(),
                backend_name=backend.name,
                backend_version=backend.backend_version,
                headers=self.headers,
                shots=self.shots,
                meas_level=self.meas_level,
                meas_return=self.meas_return,
                memory=self.remote_data.result.memory,
            )
        return self._result

    def __repr__(self) -> str:
        return f"<Job {self.job_id()} on {self.backend().name}: {self._status.name}>"
