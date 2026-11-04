# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""The calls the SDK makes to the backends, each to the URL and with the token of its job"""
import tempfile
from pathlib import Path
from typing import Dict

import httpx

from .bcc_models import JobFile
from .client import TRANSFER_TIMEOUT, raise_for_error


def upload_job(
    client: httpx.Client, url: str, job_file: JobFile, access_token: str
) -> None:
    """Uploads the job to the backend that runs it

    Args:
        client: the client of the backends
        url: the URL MSS gave to upload the job to
        job_file: the job
        access_token: the token MSS gave for the job

    Raises:
        ApiError: Failed to POST job '{job_id}': {detail}
    """
    content = job_file.model_dump_json(indent=2).encode("utf-8")
    response = client.post(
        url,
        files={"upload_file": (f"{job_file.job_id}.json", content, "application/json")},
        headers=_get_auth_headers(access_token),
        timeout=TRANSFER_TIMEOUT,
    )
    raise_for_error(response, f"Failed to POST job '{job_file.job_id}'")


def cancel_job(
    client: httpx.Client, upload_url: str, job_id: str, access_token: str
) -> None:
    """Cancels the job on the backend that runs it

    Args:
        client: the client of the backends
        upload_url: the URL the job was uploaded to
        job_id: the id of the job
        access_token: the token MSS gave for the job

    Raises:
        ApiError: Failed to cancel job '{job_id}': {detail}
    """
    response = client.post(
        f"{upload_url}/{job_id}/cancel",
        json={},
        headers=_get_auth_headers(access_token),
    )
    raise_for_error(response, f"Failed to cancel job '{job_id}'")


def download_logfile(
    client: httpx.Client, url: str, job_id: str, access_token: str
) -> Path:
    """Downloads the job's logfile into the temporary folder

    Args:
        client: the client of the backends
        url: the job's download URL
        job_id: the id of the job
        access_token: the token MSS gave for the job

    Returns:
        the path of the downloaded logfile

    Raises:
        ApiError: Failed to GET logfile of job '{job_id}': {detail}
    """
    logfile = Path(tempfile.gettempdir()) / f"{job_id}.hdf5"
    headers = _get_auth_headers(access_token)
    with client.stream(
        "GET", url, headers=headers, timeout=TRANSFER_TIMEOUT
    ) as response:
        if not response.is_success:
            response.read()
            raise_for_error(response, f"Failed to GET logfile of job '{job_id}'")
        with logfile.open("wb") as file:
            # iter_bytes decodes any Content-Encoding, which response.raw did not
            for chunk in response.iter_bytes():
                file.write(chunk)
    return logfile


def _get_auth_headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
