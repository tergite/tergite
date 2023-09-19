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
import functools

from typing import List, Optional, Tuple

import requests
from qiskit.providers.providerutils import filter_backends

from qiskit.providers import ProviderV1

from .backend import OpenPulseBackend, OpenQASMBackend, TergiteBackendConfig
from .config import REST_API_MAP
from .provider_account import ProviderAccount


class Provider(ProviderV1):
    def __init__(self, /, account: ProviderAccount):
        super().__init__()
        self.provider_account = account
        self._malformed_backends = {}

    def backends(self, /, name: str = None, filters: callable = None, **kwargs) -> list:
        """
        Filter the available backends of this provider.
        Return value is a list of instantiated and available backends.
        """
        available_backends = self.available_backends
        if name in self._malformed_backends:
            exp = {self._malformed_backends[name]}
            raise TypeError(f"malformed backend '{name}', {exp}")

        if name:
            kwargs["backend_name"] = name

        return filter_backends(available_backends.values(), filters=filters, **kwargs)

    @functools.cached_property
    def available_backends(self, /) -> dict:
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

        auth = self._get_account_basic_auth()
        # set up headers
        headers = {}
        if self.provider_account.token:
            headers["Authorization"] = f"Bearer {self.provider_account.token}"

        response = requests.get(url=url, auth=auth, headers=headers)
        if not response.ok:
            raise RuntimeError(f"GET request for backends timed out. GET {url}")

        records = response.json()
        for record in records:
            try:
                parsed_data.append(TergiteBackendConfig(**record))
            except TypeError as exp:
                self._malformed_backends[record["name"]] = f"{exp}\n{exp.__traceback__}"

        return parsed_data
        
    def _get_account_basic_auth(self) -> Optional[Tuple[str, str]]:
        """Retrieves the account's basic auth if any.
        
        Returns:
            tuple of (username, password) if account has auth else None
        """
        try:
            username = self.provider_account.extras["username"]
            password = self.provider_account.extras.get("password", "")
            return username, password
        except (TypeError, KeyError):
            return None

    def __str__(self, /):
        return "Tergite: Provider"

    def __repr__(self, /):
        return "<{} from Tergite Qiskit>".format(self.__class__.__name__)