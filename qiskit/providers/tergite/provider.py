# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
import functools

import requests
from qiskit.providers.providerutils import filter_backends

from qiskit.providers import ProviderV1

from .backend import OpenPulseBackend, OpenQASMBackend
from .config import REST_API_MAP


class Provider(ProviderV1):
    def __init__(self, /, account: object):
        super().__init__()
        self.provider_account = account

    def backends(self, /, name: str = None, filters: callable = None, **kwargs) -> list:
        """
        Filter the available backends of this provider.
        Return value is a list of instantiated and available backends.
        """
        if name:
            kwargs["backend_name"] = name

        return filter_backends(
            self.available_backends.values(), filters=filters, **kwargs
        )

    @functools.cached_property
    def available_backends(self, /) -> dict:
        backends = dict()

        response = requests.get(self.provider_account.url + REST_API_MAP["backends"])
        if not response.ok:
            raise RuntimeError(
                f"GET request for backends timed out. GET {self.provider_account.url}"
                + REST_API_MAP["backends"]
            )

        for backend_dict in response.json():
            if backend_dict["open_pulse"]:
                obj = OpenPulseBackend(
                    data=backend_dict, provider=self, base_url=self.provider_account.url
                )
            else:
                obj = OpenQASMBackend(
                    data=backend_dict, provider=self, base_url=self.provider_account.url
                )
            backends[obj.name] = obj

        return backends

    def __str__(self, /):
        return "Tergite: Provider"

    def __repr__(self, /):
        return "<{} from Tergite Qiskit>".format(self.__class__.__name__)
