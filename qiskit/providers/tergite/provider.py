# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


from qiskit.providers import BaseProvider
from qiskit.providers.models import QasmBackendConfiguration, PulseBackendConfiguration
from qiskit.providers.providerutils import filter_backends
from .backend import Backend
from .hardcoded_backend_data import configuration as pingu_cfg_dict


class Provider(BaseProvider):
    def __init__(self):
        super().__init__()

        print("Tergite: Provider init called")
        self._backends = None

    def backends(self, name=None, filters=None, **kwargs):
        # TODO: decide if we should always fetch from DB, or do it only once
        self._backends = self._fetch_backends()
        backends = self._backends.values()

        if name:
            kwargs["backend_name"] = name

        return filter_backends(backends, filters=filters, **kwargs)

    def _fetch_backends(self):
        # TODO: fetch available backends from DB

        backends = {}

        try:

            backend_config = QasmBackendConfiguration.from_dict(pingu_cfg_dict)
            backends[backend_config.backend_name] = Backend(
                configuration=backend_config, provider=self
            )
        except TypeError as ex:
            backend_name = pingu_cfg_dict.get("backend_name", "unknown")
            print(f"Tergite: Backend {backend_name} configuration failed")

        return backends

    def __str__(self):
        return "Tergite: Provider"

    def __repr__(self):
        return "<{} from Tergite Qiskit>".format(self.__class__.__name__)
