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
from qiskit.providers import ProviderV1
from qiskit.providers.providerutils import filter_backends

# TODO: fetch available backends from DB
from .hardcoded_backend_data import hardcoded_backends


class Provider(ProviderV1):
    def __init__(self, /, account: object):
        super().__init__()

        self._backends = None
        self._provider_account = account

    def backends(self, /, name: str = None, filters: callable = None, **kwargs) -> list:
        """
        Filter the available backends of this provider.
        Return value is a list of instantiated and available backends.
        """
        # TODO: decide if we should always fetch from DB, or do it only once
        self._backends = self._fetch_backends()
        backends = self._backends.values()

        if name:
            kwargs["backend_name"] = name

        return filter_backends(backends, filters=filters, **kwargs)

    def _fetch_backends(self, /) -> dict:
        """
        Fetch all the backends of this provider.
        Key of return dict is name of backend.
        Value of return dict is instantiated backend object.
        """
        backends = dict()
        for backend in hardcoded_backends:
            obj = backend(provider=self, base_url=self._provider_account.url)
            backends[obj.name] = obj

        return backends

    def __str__(self, /):
        return "Tergite: Provider"

    def __repr__(self, /):
        return "<{} from Tergite Qiskit>".format(self.__class__.__name__)
