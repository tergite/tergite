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
"""The client of MSS: the devices, their calibrations, and the jobs registered on them"""

import warnings
from typing import Callable, List, Optional

import httpx
from pydantic import ValidationError

from ...utils.http import REQUEST_TIMEOUT, get_ssl_context, raise_for_error
from . import models


class MssClient:
    """The client of an MSS, which sends an account's app token with each request"""

    def __init__(self, url: str, get_token: Callable[[], Optional[str]]):
        """Initializes the client

        Args:
            url: the root URL of MSS
            get_token: gets the app token, or None for an MSS that asks for none; it is
                called for each request, so that a token changed on the account is used
        """
        self._get_token = get_token
        self._http = httpx.Client(
            base_url=url,
            auth=self._authenticate,
            timeout=REQUEST_TIMEOUT,
            verify=get_ssl_context(),
        )

    def get_devices(self) -> List[models.Device]:
        """Gets the devices MSS lists, skipping, with a warning, any the SDK cannot read

        Returns:
            the devices

        Raises:
            ApiError: Error retrieving backends: {detail}
        """
        response = self._http.get("/devices/")
        raise_for_error(response, "Error retrieving backends")

        devices = []
        for item in response.json()["data"]:
            try:
                devices.append(models.Device.model_validate(item))
            except ValidationError as exp:
                fields = ", ".join(
                    ".".join(map(str, err["loc"])) for err in exp.errors()
                )
                warnings.warn(
                    f"Skipping malformed device '{item.get('name')}': {fields}"
                )
        return devices

    def get_calibration(self, backend_name: str) -> models.DeviceCalibration:
        """Gets the latest calibration of the device

        Args:
            backend_name: the name of the device

        Returns:
            the device's calibration

        Raises:
            ApiError: failed to get device calibrations for '{backend_name}': {detail}
        """
        response = self._http.get(f"/calibrations/{backend_name}")
        raise_for_error(
            response, f"failed to get device calibrations for '{backend_name}'"
        )
        return models.DeviceCalibration.model_validate(response.json())

    def create_job(
        self, backend_name: str, calibration_date: Optional[str]
    ) -> models.CreatedJobResponse:
        """Registers a new job on the device

        Args:
            backend_name: the name of the device
            calibration_date: when the calibration the job was compiled with was made

        Returns:
            the job's id, and the URL and token to upload it with

        Raises:
            ApiError: unable to register job at the remote API: {detail}
        """
        response = self._http.post(
            "/jobs/",
            json={"device": backend_name, "calibration_date": calibration_date},
        )
        raise_for_error(response, "unable to register job at the remote API")
        return models.CreatedJobResponse.model_validate(response.json())

    def get_job(self, job_id: str) -> models.Job:
        """Gets the job as MSS has it

        Args:
            job_id: the id of the job

        Returns:
            the job

        Raises:
            ApiError: error retrieving job data: {detail}
        """
        response = self._http.get(f"/jobs/{job_id}")
        raise_for_error(response, "error retrieving job data")
        return models.Job.model_validate(response.json())

    def delete_job(self, job_id: str) -> None:
        """Deletes the job at MSS, and at its backend if the backend has it

        Args:
            job_id: the id of the job

        Raises:
            ApiError: unable to delete job at the remote API: {detail}
        """
        response = self._http.delete(f"/jobs/{job_id}")
        raise_for_error(response, "unable to delete job at the remote API")

    def _authenticate(self, request: httpx.Request) -> httpx.Request:
        """Adds the account's app token, as it is now, to the request"""
        token = self._get_token()
        if token is not None:
            request.headers["Authorization"] = f"Bearer {token}"
        return request
