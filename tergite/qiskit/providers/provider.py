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
"""Defines the Qiskit provider with which to access the Tergite Quantum Computers"""
import functools
from typing import Dict, List, Optional, Union

import requests
from qiskit.providers import ProviderV1
from qiskit.providers.providerutils import filter_backends

from .backend import OpenPulseBackend, OpenQASMBackend, TergiteBackendConfig
from .config import REST_API_MAP
from .provider_account import ProviderAccount


class Provider(ProviderV1):
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

    def _get_backend_configs(self) -> List[TergiteBackendConfig]:
        """Retrieves the backend configs from which to construct Backend objects"""
        parsed_data = []
        url = f"{self.provider_account.url}{REST_API_MAP['backends']}"

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
