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
from typing import Any, Callable, Dict, List

from qiskit.providers.providerutils import filter_backends

from ..accounts import Account
from ..api import mss
from ..api.client import create_bcc_client, create_mss_client
from ..backend import TergiteBackend
from ..exc import BackendNotFoundError
from ..job import STATUS_MAP, Job


class Provider:
    """The Qiskit Provider with which to access the Tergite quantum computers"""

    def __init__(self, /, account: Account):
        """Initializes the Provider

        Args:
            account: the account at the Tergite service to connect to
        """
        super().__init__()
        self.account = account
        self.mss_client = create_mss_client(account.url, lambda: self.account.token)
        self.bcc_client = create_bcc_client()

    def backends(
        self, /, name: str = None, filters: Callable[[Any], bool] = None, **kwargs
    ) -> List[TergiteBackend]:
        """Filters the available backends of this provider.

        Args:
            name: the name of the backend
            filters: a callable to filter the backends with
            kwargs: kwargs to match the available backends with

        Returns:
            A list of the available backends
                that match the given filter
        """
        available_backends = list(self.available_backends.values())
        if name:
            # by name first, as filter_backends builds the target of each backend it reads
            available_backends = [b for b in available_backends if b.name == name]

        return filter_backends(available_backends, filters=filters, **kwargs)

    @property
    def available_backends(self, /) -> Dict[str, TergiteBackend]:
        """The backends of the devices MSS lists, by name, fetched on each read so that a
        device coming online is seen"""
        return {
            device.name: TergiteBackend(
                data=device, provider=self, base_url=self.account.url
            )
            for device in mss.get_devices(self.mss_client)
        }

    def job(self, job_id: str) -> Job:
        """Retrieve a runtime job given a job id

        MSS does not keep how a job was run, so its measurement level and shots are taken
        from the memory it returns, and its circuits' registers are unknown: counts come
        keyed by their bits, without register names or leading zeros.

        Args:
            job_id: the ID of the job

        Returns:
            an instance of `Job` corresponding to the given job id
        """
        remote_data = mss.get_job(self.mss_client, job_id)
        memory = remote_data.result.memory if remote_data.result else []
        is_counts = bool(memory) and bool(memory[0]) and isinstance(memory[0][0], str)
        return Job(
            backend=self.get_backend(name=remote_data.device),
            job_id=job_id,
            shots=len(memory[0]) if memory else None,
            meas_level=2 if is_counts else 1,
            status=STATUS_MAP.get(remote_data.status),
            remote_data=remote_data,
            download_url=remote_data.download_url,
            calibration_date=remote_data.calibration_date,
            access_token=remote_data.access_token,
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

    def get_backend(self, name=None, **kwargs) -> TergiteBackend:
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
