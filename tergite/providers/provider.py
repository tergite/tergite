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

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from qiskit.providers.providerutils import filter_backends

from ..backends.backend import TergiteBackend
from ..clients.bcc import BccClient
from ..clients.mss import MssClient
from ..exc import BackendNotFoundError
from ..jobs.job import STATUS_MAP, Job
from ..jobs.results import CircuitHeader
from .accounts import Account

if TYPE_CHECKING:
    from ..clients.mss.models import JobResult


class Provider:
    """The Qiskit Provider with which to access the Tergite quantum computers"""

    def __init__(self, /, account: Account):
        """Initializes the Provider

        Args:
            account: the account at the Tergite service to connect to
        """
        super().__init__()
        self.account = account
        self.mss_client = MssClient(account.url, lambda: self.account.token)
        self.bcc_client = BccClient()

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
            for device in self.mss_client.get_devices()
        }

    def job(self, job_id: str) -> Job:
        """Retrieve a runtime job given a job id

        A backend sends how it ran the job with its result: the shots, measurement level
        and each circuit's name and classical bits, so counts come with the circuits' names
        and every bit, though not their registers' names. Of a job an older backend ran,
        the shots and level are taken from the memory, and counts come keyed by their bits
        without leading zeros.

        Args:
            job_id: the ID of the job

        Returns:
            an instance of `Job` corresponding to the given job id
        """
        remote_data = self.mss_client.get_job(job_id)
        result = remote_data.result
        return Job(
            backend=self.get_backend(name=remote_data.device),
            job_id=job_id,
            headers=_get_result_headers(result),
            shots=_get_result_shots(result),
            meas_level=_get_result_meas_level(result),
            meas_return=_get_result_meas_return(result),
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


def _get_result_headers(result: Optional["JobResult"]) -> Optional[List[CircuitHeader]]:
    """Gets each circuit's header from those the result was sent with; none if it was not"""
    if result is None or not result.circuits:
        return None
    return [
        CircuitHeader(name=circuit.name, creg_sizes=[], memory_slots=circuit.num_clbits)
        for circuit in result.circuits
    ]


def _get_result_shots(result: Optional["JobResult"]) -> Optional[int]:
    """Gets the shots the result was sent with, or else those of its memory"""
    if result is None:
        return None
    if result.shots is not None:
        return result.shots
    memory = result.memory or []
    return len(memory[0]) if memory else None


def _get_result_meas_level(result: Optional["JobResult"]) -> int:
    """Gets the measurement level the result was sent with, or else 2 for a memory of
    counts and 1 for one of IQ points"""
    if result is not None and result.meas_level is not None:
        return int(result.meas_level)
    memory = (result.memory if result else None) or []
    is_counts = bool(memory) and bool(memory[0]) and isinstance(memory[0][0], str)
    return 2 if is_counts else 1


def _get_result_meas_return(result: Optional["JobResult"]) -> str:
    """Gets what the result was sent with, single for each shot's or avg for their average;
    single if it was not"""
    if result is None or result.meas_return is None:
        return "single"
    return result.meas_return.value
