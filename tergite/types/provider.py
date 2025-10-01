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
# Martin Ahindura, 2023, 2025
# Adilet Tuleuov, 2024

"""Defines the Qiskit provider with which to access the Tergite Quantum Computers"""
import functools
from typing import Dict, List, Union

from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends

from ..services import api_client
from ..services.configs import AccountInfo
from ..utils.job_file import extract_job_metadata, extract_job_qobj
from .backend import (
    OpenPulseBackend,
    OpenQASMBackend,
)
from .job import STATUS_MAP, Job


class Provider:
    """The Qiskit Provider with which to access the Tergite quantum computers"""

    def __init__(self, /, account: "AccountInfo"):
        """Initializes the Provider

        Args:
            account: the instance of the
                :class:tergite.providers.tergite.account.AccountInfo`
                with which to connect to the Tergite API
        """
        super().__init__()
        self.account = account
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
        available_backends = self.available_backends.values()
        if name:
            kwargs["backend_name"] = name

        return filter_backends(available_backends, filters=filters, **kwargs)

    @functools.cached_property
    def available_backends(
        self, /
    ) -> Dict[str, Union[OpenPulseBackend, OpenQASMBackend]]:
        """Dictionary of all available backends got from the API"""
        backends = dict()
        backend_configs = api_client.get_backend_configs(self.account)

        for backend_conf in backend_configs:
            if backend_conf.open_pulse:
                obj = OpenPulseBackend(
                    data=backend_conf, provider=self, base_url=self.account.url
                )
            else:
                obj = OpenQASMBackend(
                    data=backend_conf, provider=self, base_url=self.account.url
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
        account = self.account
        remote_data = api_client.get_remote_job_data(account, job_id=job_id)
        if remote_data.download_url is None:
            raise RuntimeError(f"Job: {job_id} has no download_url")

        download_url = remote_data.download_url
        access_token = remote_data.access_token
        backend = self.get_backend(name=remote_data.device)
        logfile = api_client.download_job_logfile(
            job_id=job_id, url=download_url, access_token=access_token
        )
        raw_status = remote_data.status
        status = STATUS_MAP.get(raw_status)
        calibration_date = remote_data.calibration_date

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
            access_token=access_token,
            **metadata,
        )

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
