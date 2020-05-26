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


# imports
import logging
from qiskit.providers import BaseProvider
from qiskit.providers.models import QasmBackendConfiguration, PulseBackendConfiguration
from qiskit.providers.providerutils import filter_backends
from .backend import Backend

logger = logging.getLogger(__name__)


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

        ret = {}

        for backend_dict_config in self.BACKENDS_CONFIGURATION:
            if not isinstance(backend_dict_config, dict):
                logger.warning(
                    "Improper backend_config retrieved. Not a dictionary. Skipping"
                )
                continue

            try:

                backend_config = QasmBackendConfiguration.from_dict(backend_dict_config)
                ret[backend_config.backend_name] = Backend(
                    configuration=backend_config, provider=self
                )

            except TypeError as ex:
                backend_name = backend_dict_config.get("backend_name", "unknown")
                logger.warning(
                    "Invalid backend '%s' configuration. Problem: %s. Skipping.",
                    backend_name,
                    ex,
                )

        return ret

    def __str__(self):
        return "Tergite: Provider"

    def __repr__(self):
        return "<{} from Tergite Qiskit>".format(self.__class__.__name__)

    BACKENDS_CONFIGURATION = [
        # pingu - taken from IBMQ 16 Melbourne configuration example
        {
            "allow_q_circuit": False,
            "allow_q_object": True,
            "backend_name": "pingu",
            "backend_version": "1.0.0",
            "basis_gates": ["u1", "u2", "u3", "cx", "id"],
            "conditional": False,
            "coupling_map": [
                [1, 0],
                [1, 2],
                [2, 3],
                [4, 3],
                [4, 10],
                [5, 4],
                [5, 6],
                [5, 9],
                [6, 8],
                [7, 8],
                [9, 8],
                [9, 10],
                [11, 3],
                [11, 10],
                [11, 12],
                [12, 2],
                [13, 1],
                [13, 12],
            ],
            "credits_required": True,
            "description": "14 qubit device",
            "gates": [
                {
                    "coupling_map": [
                        [0],
                        [1],
                        [2],
                        [3],
                        [4],
                        [5],
                        [6],
                        [7],
                        [8],
                        [9],
                        [10],
                        [11],
                        [12],
                        [13],
                    ],
                    "name": "id",
                    "parameters": [],
                    "qasm_def": "gate id q { U(0,0,0) q; }",
                },
                {
                    "coupling_map": [
                        [0],
                        [1],
                        [2],
                        [3],
                        [4],
                        [5],
                        [6],
                        [7],
                        [8],
                        [9],
                        [10],
                        [11],
                        [12],
                        [13],
                    ],
                    "name": "u1",
                    "parameters": ["lambda"],
                    "qasm_def": "gate u1(lambda) q { U(0,0,lambda) q; }",
                },
                {
                    "coupling_map": [
                        [0],
                        [1],
                        [2],
                        [3],
                        [4],
                        [5],
                        [6],
                        [7],
                        [8],
                        [9],
                        [10],
                        [11],
                        [12],
                        [13],
                    ],
                    "name": "u2",
                    "parameters": ["phi", "lambda"],
                    "qasm_def": "gate u2(phi,lambda) q { U(pi/2,phi,lambda) q; }",
                },
                {
                    "coupling_map": [
                        [0],
                        [1],
                        [2],
                        [3],
                        [4],
                        [5],
                        [6],
                        [7],
                        [8],
                        [9],
                        [10],
                        [11],
                        [12],
                        [13],
                    ],
                    "name": "u3",
                    "parameters": ["theta", "phi", "lambda"],
                    "qasm_def": "u3(theta,phi,lambda) q { U(theta,phi,lambda) q; }",
                },
                {
                    "coupling_map": [
                        [1, 0],
                        [1, 2],
                        [2, 3],
                        [4, 3],
                        [4, 10],
                        [5, 4],
                        [5, 6],
                        [5, 9],
                        [6, 8],
                        [7, 8],
                        [9, 8],
                        [9, 10],
                        [11, 3],
                        [11, 10],
                        [11, 12],
                        [12, 2],
                        [13, 1],
                        [13, 12],
                    ],
                    "name": "cx",
                    "parameters": [],
                    "qasm_def": "gate cx q1,q2 { CX q1,q2; }",
                },
            ],
            "local": False,
            "max_experiments": 150,
            "max_shots": 8192,
            "memory": False,
            "n_qubits": 14,
            "n_registers": 1,
            "online_date": "2018-11-06T05:00:00Z",
            "open_pulse": False,
            "sample_name": "albatross",
            "simulator": False,
            "url": "None",
        }
    ]
