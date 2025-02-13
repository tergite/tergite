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
# This code was refactored from the original on 22nd September, 2023 by Martin Ahindura
# This code was altered from the original on 25th of Septeber, 2024 by Adilet Tuleuov

"""Defines the Qiskit provider with which to access the Tergite Quantum Computers"""
import functools
import json
import shutil
import tempfile
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import requests
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends
from requests import Response

from .backend import (
    DeviceCalibrationV2,
    OpenPulseBackend,
    OpenQASMBackend,
    TergiteBackendConfig,
)
from .config import REST_API_MAP
from .job import STATUS_MAP, Job
from .logfile import extract_job_metadata, extract_job_qobj
from .provider_account import ProviderAccount
from .serialization import IQXJsonEncoder


class Provider:
    """The Qiskit Provider with which to access the Tergite quantum computers"""

    def __init__(self, /, account: ProviderAccount):
        """Initializes the Provider

        Args:
            account: the instance of the
                :class:tergite.providers.tergite.provider_account.ProviderAccount`
                with which to connect to the Tergite API
        """
        super().__init__()
        self.provider_account = account
        self._malformed_backends = {}

    def backends(
        self, /, name: str = None, filters: callable = None, **kwargs
    ) -> List[Union[OpenPulseBackend, OpenQASMBackend]]:
        """Filters the available backends of this provider.

        Args:
            name: the name of the backend
            filters: a callable to filter the backends with
            kwargs: kwargs to match the available backends with

        Returns:
            A list of instantiated and available OpenPulseBackend, or OpenPulseBackend backends,
                that match the given filter
        """
        available_backends = self.available_backends
        if name in self._malformed_backends:
            exp = self._malformed_backends[name]
            raise TypeError(f"malformed backend '{name}', {exp}")

        if name:
            kwargs["backend_name"] = name

        return filter_backends(available_backends.values(), filters=filters, **kwargs)

    @functools.cached_property
    def available_backends(
        self, /
    ) -> Dict[str, Union[OpenPulseBackend, OpenQASMBackend]]:
        """Dictionary of all available backends got from the API"""
        backends = dict()
        backend_configs = self._get_backend_configs()

        for backend_conf in backend_configs:
            if backend_conf.open_pulse:
                obj = OpenPulseBackend(
                    data=backend_conf, provider=self, base_url=self.provider_account.url
                )
            else:
                obj = OpenQASMBackend(
                    data=backend_conf, provider=self, base_url=self.provider_account.url
                )
            backends[obj.name] = obj

        return backends

    def job(self, job_id: str) -> Job:
        """Retrieve a runtime job given a job id

        Args:
            job_id: the ID of the job

        Returns:
            an instance of `Job` corresponding to the given job id

        Raises:
            RuntimeError: Job: {job_id} has no download_url
        """
        remote_data = self.get_remote_job_data(job_id)
        if "download_url" not in remote_data:
            raise RuntimeError(f"Job: {job_id} has no download_url")

        download_url = remote_data["download_url"]
        backend = self.get_backend(name=remote_data["backend"])
        logfile = self.download_job_logfile(job_id, url=remote_data["download_url"])
        raw_status = remote_data.get("status")
        status = STATUS_MAP.get(raw_status)
        calibration_date = remote_data.get("calibration_date")

        metadata = extract_job_metadata(logfile)
        payload = extract_job_qobj(logfile)

        return Job(
            backend=backend,
            job_id=job_id,
            payload=payload,
            upload_url=None,
            download_url=download_url,
            logfile=logfile,
            status=status,
            remote_data=remote_data,
            calibration_date=calibration_date,
            **metadata,
        )

    def _get_backend_configs(self) -> List[TergiteBackendConfig]:
        """Retrieves the backend configs from the remote API

         These configs are used to construct Backend objects

        Raises:
            RuntimeError: Error retrieving backends: {detail}

        Returns:
            list of TergiteBackendConfig got from the remote API
        """
        parsed_data = []
        url = f"{self.provider_account.url}{REST_API_MAP['devices']}"

        # reset malformed backends map
        self._malformed_backends.clear()

        response = requests.get(url=url, headers=self.get_auth_headers())
        if not response.ok:
            error_msg = _get_err_text(response)
            raise RuntimeError(f"Error retrieving backends: {error_msg}")

        records = response.json()
        for record in records:
            try:
                parsed_data.append(TergiteBackendConfig(**record))
            except TypeError as exp:
                self._malformed_backends[record["name"]] = f"{exp}"

        return parsed_data

    def get_latest_calibration(
        self, backend_name: Optional[str] = None
    ) -> DeviceCalibrationV2:
        """Retrieves the latest backend calibration data and returns Calibration objects

        Args:
            backend_name: the name of the backend

        Returns:
            the DeviceCalibrationV2 for the given backend

        Raises:
            RuntimeError: Failed to get device calibrations for '{backend_name}': {error_msg}
            ValueError: Error parsing device calibration data for '{backend_name}': {detail}
        """
        url = (
            f"{self.provider_account.url}{REST_API_MAP['calibrations']}/{backend_name}"
        )
        headers = self.get_auth_headers()
        response = requests.get(url, headers=headers)

        if not response.ok:
            error_msg = _get_err_text(response)
            raise RuntimeError(
                f"failed to get device calibrations for '{backend_name}': {error_msg}"
            )

        try:
            return DeviceCalibrationV2(**response.json())
        except Exception as e:
            raise ValueError(
                f"Error parsing device calibration data for '{backend_name}': {e}"
            ) from e

    def get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Retrieves the auth header for this provider.

        Returns:
            dict of authorization of the authorization headers if account has auth else None
        """
        if self.provider_account.token:
            return {"Authorization": f"Bearer {self.provider_account.token}"}

        return None

    def register_job_on_api(
        self, backend_name: str, calibration_date: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Registers the job on the remote API

        Args:
            backend_name: the name of the backend
            calibration_date: the current last_calibrated timestamp for the given backend

        Returns:
            a dict with the response from the API

        Raises:
            RuntimeError: unable to register job at the remote API: {detail}
        """
        url = f"{self.provider_account.url}{REST_API_MAP['jobs']}"
        params = {"backend": backend_name, "calibration_date": calibration_date}
        response = requests.post(url, headers=self.get_auth_headers(), params=params)
        if not response.ok:
            err_msg = _get_err_text(response)
            raise RuntimeError(f"unable to register job at the remote API: {err_msg}")

        return response.json()

    def send_job_file(self, url: str, job_data: Dict[str, Any]) -> Response:
        """Sends the job file to the remote server

        Args:
            url: the URL to send the job file to
            job_data: the data of the job

        Returns:
            the response after the submission

        Raises:
            RuntimeError: Failed to POST job '{job_id}': {detail}
        """
        path = Path(tempfile.gettempdir()) / str(uuid4())

        try:
            with path.open("w+") as file:
                json.dump(job_data, file, cls=IQXJsonEncoder, indent="\t")
                response = requests.post(
                    url, files={"upload_file": file}, headers=self.get_auth_headers()
                )
                # FIXME: Can the backend update the MSS when a job is queued i.e. after this request?
                if not response.ok:
                    error_msg = _get_err_text(response)
                    raise RuntimeError(
                        f"Failed to POST job '{job_data['job_id']}': {error_msg}"
                    )
        finally:
            # Delete temporary file
            path.unlink()

        return response

    def download_job_logfile(self, job_id: str, url: str) -> Path:
        """Downloads the job logfile and returns the path to the downloaded file

        Args:
            job_id: the id of the job
            url: the URL to download from

        Returns:
            the path to the downloaded job file

        Raises:
            RuntimeError: Failed to GET logfile of job '{job_id}': {detail}
        """
        file_response = requests.get(url, stream=True, headers=self.get_auth_headers())
        if not file_response.ok:
            error_msg = _get_err_text(file_response)
            raise RuntimeError(f"Failed to GET logfile of job '{job_id}': {error_msg}")

        job_logfile = Path(tempfile.gettempdir()) / (job_id + ".hdf5")
        with open(job_logfile, "wb") as file:
            shutil.copyfileobj(file_response.raw, file)

        return job_logfile

    def get_remote_job_data(self, job_id: str, /) -> Dict[str, Any]:
        """Retrieves the job data from the remote API

        Args:
            job_id: the ID of the job to retrieve

        Returns:
            the dict representation of the job in the remote API

        Raises:
            RuntimeError: error retrieving job data: {detail}
        """
        url = f"{self.provider_account.url}{REST_API_MAP['jobs']}/{job_id}"
        response = requests.get(url, headers=self.get_auth_headers())
        if response.ok:
            return response.json()

        error_msg = _get_err_text(response)
        raise RuntimeError(f"error retrieving job data: {error_msg}")

    def __str__(self, /):
        return "Tergite: Provider"

    def __repr__(self, /):
        return "<{} from Tergite Qiskit>".format(self.__class__.__name__)

    # The below code is part of Qiskit.
    #
    # (C) Copyright IBM 2020.
    #
    # This code is licensed under the Apache License, Version 2.0. You may
    # obtain a copy of this license in the LICENSE.txt file in the root directory
    # of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
    #
    # Any modifications or derivative works of this code must retain this
    # copyright notice, and modified files need to carry a notice indicating
    # that they have been altered from the originals.
    #
    # This code is part of Tergite
    #
    # (C) Chalmers Next Labs (2024)
    #
    # This code is licensed under the Apache License, Version 2.0. You may
    # obtain a copy of this license in the LICENSE.txt file in the root directory
    # of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
    #
    # Any modifications or derivative works of this code must retain this
    # copyright notice, and modified files need to carry a notice indicating
    # that they have been altered from the originals.
    #
    # ---------------- ALTERATION NOTICE ---------------- #
    # This code has been derived from the Qiskit abstract ProviderV1 class

    def get_backend(
        self, name=None, **kwargs
    ) -> Union[OpenPulseBackend, OpenQASMBackend]:
        """Return a single backend matching the specified filtering.

        Args:
            name (str): name of the backend.
            **kwargs: dict used for filtering.

        Returns:
            Backend: a backend matching the filtering.

        Raises:
            QiskitBackendNotFoundError: if no backend could be found or
                more than one backend matches the filtering criteria.
        """
        # As Qiskit ProviderV1 class was deprecated
        # See: https://github.com/Qiskit/qiskit/pull/12145

        # This class was migrated from Abstract ProviderV1 class
        # From: https://github.com/Qiskit/qiskit/blob/1.2.2/qiskit/providers/provider.py#L53

        backends = self.backends(name, **kwargs)
        if len(backends) > 1:
            raise QiskitBackendNotFoundError(
                "More than one backend matches the criteria"
            )
        if not backends:
            raise QiskitBackendNotFoundError("No backend matches the criteria")

        return backends[0]


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
