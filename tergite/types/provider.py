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
from typing import Any, Callable, Dict, List, Union

from qiskit.providers.providerutils import filter_backends

from ..api import bcc, mss
from ..api.client import create_bcc_client, create_mss_client
from ..exc import ApiError, BackendNotFoundError
from ..services.configs import AccountInfo
from ..utils.job_file import extract_job_metadata, extract_job_qobj
from .backend import OpenPulseBackend, OpenQASMBackend
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
        self.mss_client = create_mss_client(account.url, lambda: self.account.token)
        self.bcc_client = create_bcc_client()

    def backends(
        self, /, name: str = None, filters: Callable[[Any], bool] = None, **kwargs
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
        available_backends = list(self.available_backends.values())
        if name:
            # by name first, as filter_backends builds the target of each backend it reads
            available_backends = [b for b in available_backends if b.name == name]

        return filter_backends(available_backends, filters=filters, **kwargs)

    @functools.cached_property
    def available_backends(
        self, /
    ) -> Dict[str, Union[OpenPulseBackend, OpenQASMBackend]]:
        """Dictionary of all available backends got from the API"""
        backends = dict()
        backend_configs = mss.get_devices(self.mss_client)

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
            ApiError: Job: {job_id} has no download_url
        """
        remote_data = mss.get_job(self.mss_client, job_id)
        if remote_data.download_url is None:
            raise ApiError(f"Job: {job_id} has no download_url")

        download_url = remote_data.download_url
        access_token = remote_data.access_token
        backend = self.get_backend(name=remote_data.device)
        logfile = bcc.download_logfile(
            self.bcc_client, url=download_url, job_id=job_id, access_token=access_token
        )
        raw_status = remote_data.status
        status = STATUS_MAP.get(raw_status)
        calibration_date = remote_data.calibration_date

        metadata = extract_job_metadata(logfile)
        payload = extract_job_qobj(logfile)

        job = Job(
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
        self._sync_backend_options_from_job(job)
        return job

    def __str__(self, /):
        return "Tergite: Provider"

    def __repr__(self, /):
        return "<{} from Tergite Qiskit>".format(self.__class__.__name__)

    def _sync_backend_options_from_job(self, job):
        # Prefer payload (source of truth), fallback to metadata
        shots = None
        if getattr(job, "payload", None) is not None:
            shots = getattr(getattr(job.payload, "config", None), "shots", None)
        if shots is None:
            shots = job.metadata.get("shots")

        if shots is not None:
            job.backend().set_options(shots=int(shots))

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
            BackendNotFoundError: if no backend could be found or
                more than one backend matches the filtering criteria.
        """
        # As Qiskit ProviderV1 class was deprecated
        # See: https://github.com/Qiskit/qiskit/pull/12145

        # This class was migrated from Abstract ProviderV1 class
        # From: https://github.com/Qiskit/qiskit/blob/1.2.2/qiskit/providers/provider.py#L53

        backends = self.backends(name, **kwargs)
        if len(backends) > 1:
            raise BackendNotFoundError("More than one backend matches the criteria")
        if not backends:
            raise BackendNotFoundError("No backend matches the criteria")

        return backends[0]
