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
"""The calls the SDK makes to MSS"""
import warnings
from typing import List, Optional

import httpx
from pydantic import ValidationError

from . import mss_models
from .client import raise_for_error


def get_devices(client: httpx.Client) -> List[mss_models.Device]:
    """Gets the devices MSS lists, skipping, with a warning, any the SDK cannot read

    Args:
        client: the client of MSS

    Returns:
        the devices

    Raises:
        ApiError: Error retrieving backends: {detail}
    """
    response = client.get("/devices/")
    raise_for_error(response, "Error retrieving backends")

    devices = []
    for item in response.json()["data"]:
        try:
            devices.append(mss_models.Device.model_validate(item))
        except ValidationError as exp:
            fields = ", ".join(".".join(map(str, err["loc"])) for err in exp.errors())
            warnings.warn(f"Skipping malformed device '{item.get('name')}': {fields}")
    return devices


def get_calibration(
    client: httpx.Client, backend_name: str
) -> mss_models.DeviceCalibration:
    """Gets the latest calibration of the device

    Args:
        client: the client of MSS
        backend_name: the name of the device

    Returns:
        the device's calibration

    Raises:
        ApiError: failed to get device calibrations for '{backend_name}': {detail}
    """
    response = client.get(f"/calibrations/{backend_name}")
    raise_for_error(response, f"failed to get device calibrations for '{backend_name}'")
    return mss_models.DeviceCalibration.model_validate(response.json())


def create_job(
    client: httpx.Client, backend_name: str, calibration_date: Optional[str]
) -> mss_models.CreatedJobResponse:
    """Registers a new job on the device

    Args:
        client: the client of MSS
        backend_name: the name of the device
        calibration_date: when the calibration the job was compiled with was made

    Returns:
        the job's id, and the URL and token to upload it with

    Raises:
        ApiError: unable to register job at the remote API: {detail}
    """
    response = client.post(
        "/jobs/", json={"device": backend_name, "calibration_date": calibration_date}
    )
    raise_for_error(response, "unable to register job at the remote API")
    return mss_models.CreatedJobResponse.model_validate(response.json())


def get_job(client: httpx.Client, job_id: str) -> mss_models.Job:
    """Gets the job as MSS has it

    Args:
        client: the client of MSS
        job_id: the id of the job

    Returns:
        the job

    Raises:
        ApiError: error retrieving job data: {detail}
    """
    response = client.get(f"/jobs/{job_id}")
    raise_for_error(response, "error retrieving job data")
    return mss_models.Job.model_validate(response.json())
