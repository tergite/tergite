# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
# (C) Copyright Martin Ahindura 2023
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
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Union

import h5py
import requests
from qiskit.providers import JobV1
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends

from tergite.qiskit.deprecated.qobj import PulseQobj

from .backend import (
    DeviceCalibrationV2,
    OpenPulseBackend,
    OpenQASMBackend,
    TergiteBackendConfig,
)
from .config import REST_API_MAP
from .job import Job
from .provider_account import ProviderAccount


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
            exp = {self._malformed_backends[name]}
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

    def get_latest_calibration(self, backend_name=None) -> DeviceCalibrationV2:
        """Get latest calibration data."""
        # TODO: Consider making it update_calibration
        # TODO: get many calibrations and filter lates by date (?)
        return self._get_backend_calibration(backend_name=backend_name)

    def job(self, job_id: str) -> JobV1:
        """Retrieve a runtime job."""
        url = f"{self.provider_account.url}{REST_API_MAP['jobs']}/{job_id}"
        auth_headers = self.get_auth_headers()
        response = requests.get(url, headers=auth_headers)

        if not response.ok:
            raise RuntimeError(f"Failed to GET memory of job: {job_id}")

        job_data = response.json()
        backend = self.get_backend(name=job_data["backend"])
        job = Job(backend=backend, job_id=job_id, upload_url="")

        try:
            job_file = _download_job_file(
                job_data["download_url"], filename=f"job_data-{job_id}.hdf5"
            )
        except KeyError:
            raise RuntimeError(f"Job: {job_id} has no download_url")

        # open the HDF5 file using h5py
        with h5py.File(job_file, "r") as hdf:
            # access the 'header' group and list its contents
            try:
                qobj_metadata = hdf["header"]["qobj_metadata"]
                # update the job metadata
                job.metadata["shots"] = qobj_metadata.attrs.get("shots", None)
                job.metadata["qobj_id"] = qobj_metadata.attrs.get("qobj_id", None)
                job.metadata["num_experiments"] = qobj_metadata.attrs.get(
                    "num_experiments", None
                )

                qobj_data = hdf["header"]["qobj_data"]
                # attach a full qobj as a payload
                experiment_data = qobj_data.attrs.get("experiment_data", None)
                job.payload = PulseQobj.from_dict(data=json.loads(experiment_data))
            except KeyError as exp:
                raise RuntimeError(
                    f"Expected 'qobj' dataset not found in 'header' group.\n{exp}"
                )

        return job

    def _get_backend_configs(self) -> List[TergiteBackendConfig]:
        """Retrieves the backend configs from which to construct Backend objects"""
        parsed_data = []
        url = f"{self.provider_account.url}{REST_API_MAP['devices']}"

        # reset malformed backends map
        self._malformed_backends.clear()

        headers = self.get_auth_headers()
        response = requests.get(url=url, headers=headers)
        if not response.ok:
            raise RuntimeError(f"GET request for backends timed out. GET {url}")

        records = response.json()
        for record in records:
            try:
                parsed_data.append(TergiteBackendConfig(**record))
            except TypeError as exp:
                self._malformed_backends[record["name"]] = f"{exp}\n{exp.__traceback__}"

        return parsed_data

    def _get_backend_calibration(self, backend_name: str = None) -> DeviceCalibrationV2:
        """Retrieves the latest backend calibration data and returns Calibration objects"""
        # Construct the URL for the calibrations endpoint
        calibrations_url = (
            f"{self.provider_account.url}{REST_API_MAP['calibrations']}/{backend_name}"
        )

        # Get authentication headers from the provider
        headers = self.get_auth_headers()

        # Make the GET request to the calibrations endpoint
        response = requests.get(url=calibrations_url, headers=headers)

        if not response.ok:
            raise RuntimeError(
                f"Failed to get device calibrations for '{backend_name}': "
                f"{response.status_code} {response.text}"
            )

        # Parse the JSON response
        data = response.json()

        # Create a DeviceCalibrationV2 object from the response data
        try:
            device_calibration = DeviceCalibrationV2(**data)
        except Exception as e:
            raise ValueError(
                f"Error parsing device calibration data for '{backend_name}': {e}"
            ) from e

        return device_calibration

    def get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Retrieves the auth header for this provider.

        Returns:
            dict of authorization of the authorization headers if account has auth else None
        """
        if self.provider_account.token:
            return {"Authorization": f"Bearer {self.provider_account.token}"}

        return None

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


def _download_job_file(download_url: str, filename: str) -> str:
    """Downloads the job file and returns the path to the downloaded file

    Args:
        download_url: the URL to download from

    Returns:
        the path to the downloaded job file

    Raises:
        ValueError: file failed to download
    """
    file_response = requests.get(download_url, stream=True)
    if not file_response.ok:
        raise ValueError("file failed to download")

    # save the file temporarily
    tempdir = tempfile.gettempdir()
    temp_file = os.path.join(tempdir, filename)
    with open(temp_file, "wb") as file:
        shutil.copyfileobj(file_response.raw, file)

    return temp_file
