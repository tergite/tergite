# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
# (C) Copyright Martin Ahindura 2023
# (C) Copyright Chalmers Next Labs 2025
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
# Adilet Tuleuov, 2024
"""Client for accessing the API"""
import json
import shutil
import tempfile
from json import JSONDecodeError
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

import requests
from pydantic import ValidationError
from requests import Response

from ...compat.qiskit.qobj.encoder import IQXJsonEncoder
from .dtos import (
    CreatedJobResponse,
    DeviceCalibration,
    JobFile,
    RemoteJob,
    TergiteBackendConfig,
)

if TYPE_CHECKING:
    from ..configs import AccountInfo


def get_backend_configs(account: "AccountInfo") -> List[TergiteBackendConfig]:
    """Retrieves the backend configs from the remote API

    These configs are used to construct Backend objects
    It ignores any malformed configs.
    The expectation is no malformed config is sent over to the client.

    Args:
        account: the provider account to use

    Raises:
        RuntimeError: Error retrieving backends: {detail}
        ValidationError: if records returned does not conform to TergiteBackendConfig schema

    Returns:
        list of TergiteBackendConfig got from the remote API
    """
    url = f"{account.url}/devices/"
    headers = _get_auth_headers(account)

    response = requests.get(url, headers=headers)
    if not response.ok:
        error_msg = _get_err_text(response)
        raise RuntimeError(f"Error retrieving backends: {error_msg}")

    records = response.json()["data"]
    parsed_records = []
    for item in records:
        try:
            parsed_records.append(TergiteBackendConfig.model_validate(item))
        except ValidationError:
            pass

    return parsed_records


def get_latest_calibration(
    account: "AccountInfo", backend_name: Optional[str] = None
) -> DeviceCalibration:
    """Retrieves the latest backend calibration data and returns Calibration objects

    Args:
        account: the provider account to use to access the API
        backend_name: the name of the backend

    Returns:
        the DeviceCalibration for the given backend

    Raises:
        RuntimeError: Failed to get device calibrations for '{backend_name}': {error_msg}
        ValidationError: if records returned does not conform to DeviceCalibration schema
        ValueError: Error parsing device calibration data for '{backend_name}': {detail}
    """
    url = f"{account.url}/calibrations/{backend_name}"
    headers = _get_auth_headers(account)
    response = requests.get(url, headers=headers)

    if not response.ok:
        error_msg = _get_err_text(response)
        raise RuntimeError(
            f"failed to get device calibrations for '{backend_name}': {error_msg}"
        )

    raw_data = response.json()
    return DeviceCalibration.model_validate(raw_data)


def register_job(
    account: "AccountInfo",
    backend_name: str,
    calibration_date: Optional[str] = None,
    **kwargs,
) -> CreatedJobResponse:
    """Registers the job on the remote API

    Args:
        account: the provider account needed to access the API
        backend_name: the name of the backend
        calibration_date: the current last_calibrated timestamp for the given backend

    Returns:
        a dict with the response from the API

    Raises:
        RuntimeError: unable to register job at the remote API: {detail}
    """
    url = f"{account.url}/jobs/"
    headers = _get_auth_headers(account)
    payload = {"device": backend_name, "calibration_date": calibration_date}
    response = requests.post(url, headers=headers, json=payload)
    if not response.ok:
        err_msg = _get_err_text(response)
        raise RuntimeError(f"unable to register job at the remote API: {err_msg}")

    raw_data = response.json()
    return CreatedJobResponse.model_validate(raw_data)


def send_job_file(
    account: "AccountInfo", url: str, job_data: JobFile, access_token: str
) -> Response:
    """Sends the job file to the remote server

    Args:
        account: the account details for accessing the API
        url: the URL to send the job file to
        job_data: the data of the job
        access_token: the temporary JWT token used for submitting jobs and downloading logfiles

    Returns:
        the response after the submission

    Raises:
        RuntimeError: Failed to POST job '{job_id}': {detail}
    """
    path = Path(tempfile.gettempdir()) / str(uuid4())

    try:
        # dump json to temporary file
        with path.open("w") as dest:
            job_data_json = job_data.model_dump_json(indent=2)
            dest.write(job_data_json)

        # Send temporary file to url
        with path.open("rb") as src:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.post(url, files={"upload_file": src}, headers=headers)

            # FIXME: Can the backend update the MSS when a job is queued i.e. after this request?
            if not response.ok:
                error_msg = _get_err_text(response)
                raise RuntimeError(
                    f"Failed to POST job '{job_data.job_id}': {error_msg}"
                )

    finally:
        # Delete temporary file
        path.unlink()

    return response


def cancel_job(upload_url: str, job_id: str, access_token: str) -> Response:
    """Cancels the job on the remote server

    Args:
        upload_url: the URL where the job file was sent to
        job_id: the unique identifier of the job
        access_token: the JWT token for accessing the backend

    Returns:
        the response after the submission

    Raises:
        RuntimeError: Failed to cancel job '{job_id}': {detail}
    """
    url = f"{upload_url}/{job_id}/cancel"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.post(url, json={}, headers=headers)
    if not resp.ok:
        error_msg = _get_err_text(resp)
        raise RuntimeError(f"Failed to cancel job '{job_id}': {error_msg}")

    return resp


def download_job_logfile(job_id: str, url: str, access_token: str) -> Path:
    """Downloads the job logfile and returns the path to the downloaded file

    Args:
        job_id: the id of the job
        url: the URL to download from
        access_token: the JWT access token for accessing the backend

    Returns:
        the path to the downloaded job file

    Raises:
        RuntimeError: Failed to GET logfile of job '{job_id}': {detail}
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    file_response = requests.get(url, stream=True, headers=headers)
    if not file_response.ok:
        error_msg = _get_err_text(file_response)
        raise RuntimeError(f"Failed to GET logfile of job '{job_id}': {error_msg}")

    job_logfile = Path(tempfile.gettempdir()) / (job_id + ".hdf5")
    with open(job_logfile, "wb") as file:
        shutil.copyfileobj(file_response.raw, file)

    return job_logfile


def get_remote_job_data(account: "AccountInfo", job_id: str) -> RemoteJob:
    """Retrieves the job data from the remote API

    Args:
        account: the account details for accessing the API
        job_id: the ID of the job to retrieve

    Returns:
        the dict representation of the job in the remote API

    Raises:
        RuntimeError: error retrieving job data: {detail}
        ValidationError: response is not a valid RemoteJob instance
    """
    url = f"{account.url}/jobs/{job_id}"
    headers = _get_auth_headers(account)
    response = requests.get(url, headers=headers)
    if response.ok:
        raw_data = response.json()
        return RemoteJob.model_validate(raw_data)

    error_msg = _get_err_text(response)
    raise RuntimeError(f"error retrieving job data: {error_msg}")


def _get_err_text(response: Response) -> str:
    """Returns the error text of the response

    Args:
        response: the response whose detail is to be returned

    Returns:
        the response error detail from the response
    """
    try:
        return response.json()["detail"]
    except (KeyError, AttributeError, JSONDecodeError):
        return response.text


def _get_auth_headers(provider_account: "AccountInfo") -> Optional[Dict[str, str]]:
    """Retrieves the auth header for this provider.

    Returns:
        dict of authorization of the authorization headers if account has auth else None
    """
    if provider_account.token is not None:
        return {"Authorization": f"Bearer {provider_account.token}"}

    return None
