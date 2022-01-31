# This code is part of Tergite
#
# (C) Copyright Andreas Bengtsson, Miroslav Dobsicek 2020
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import datetime
from dateutil.tz import tzutc

# Note: Both the backend configuration and its properties are very crude
# and do not reflect Pingu A setup fully. Rather, these dictionaries are
# the first approximation which makes Qiskit Terra to work with Pingu A
# backend.
#
# Configuration is currently updated to 3 qubits. Properties are only for
# 2 qubits.

configuration = {
    "allow_object_storage": True,
    "allow_q_circuit": False,
    "allow_q_object": True,
    "backend_name": "pingu",
    "backend_version": "0.0.1",
    "basis_gates": ["u1", "u2", "u3", "rx", "ry", "rz", "x", "y", "z", "h", "cz", "cx"],
    "conditional": False,
    "coupling_map": [[0, 1], [1, 0], [0, 2], [2, 0]],
    "credits_required": False,
    "description": "2 qubit device",
    "gates": [
        {
            "coupling_map": [[0], [1], [2]],
            "name": "id",
            "parameters": [],
            "qasm_def": "gate id q { U(0,0,0) q; }",
        },
        {
            "coupling_map": [[0], [1], [2]],
            "name": "u1",
            "parameters": ["lambda"],
            "qasm_def": "gate u1(lambda) q { U(0,0,lambda) q; }",
        },
        {
            "coupling_map": [[0], [1], [2]],
            "name": "u2",
            "parameters": ["phi", "lambda"],
            "qasm_def": "gate u2(phi,lambda) q { U(pi/2,phi,lambda) " "q; }",
        },
        {
            "coupling_map": [[0], [1], [2]],
            "name": "u3",
            "parameters": ["theta", "phi", "lambda"],
            "qasm_def": "gate u3(theta,phi,lambda) q { " "U(theta,phi,lambda) q; }",
        },
        {
            "coupling_map": [[0, 1], [1, 0], [0, 2], [2, 0]],
            "name": "cz",
            "parameters": [],
            "qasm_def": "gate cz q1,q2 { CZ q1,q2; }",
        },
    ],
    "local": False,
    "max_experiments": 1,
    "max_shots": 8192,
    "meas_map": [[0, 1, 2]],
    "memory": True,
    "n_qubits": 3,
    "n_registers": 1,
    "online_date": datetime.datetime(2019, 9, 13, 4, 0, tzinfo=tzutc()),
    "open_pulse": False,
    "quantum_volume": 16,
    "sample_name": "DD",
    "simulator": False,
    "url": "None",
}

properties = {
    "backend_name": "pingu",
    "backend_version": "0.0.1",
    "gates": [
        {
            "gate": "id",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 11, 3, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.000323041374349054,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 35.55555555555556,
                },
            ],
            "qubits": [0],
        },
        {
            "gate": "u1",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 11, 3, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 0,
                },
            ],
            "qubits": [0],
        },
        {
            "gate": "u2",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 11, 3, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.000323041374349054,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 35.55555555555556,
                },
            ],
            "qubits": [0],
        },
        {
            "gate": "u3",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 11, 3, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.0006459783929685381,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 71.11111111111111,
                },
            ],
            "qubits": [0],
        },
        {
            "gate": "id",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 11, 43, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.0003435938297472628,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 35.55555555555556,
                },
            ],
            "qubits": [1],
        },
        {
            "gate": "u1",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 11, 43, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 0,
                },
            ],
            "qubits": [1],
        },
        {
            "gate": "u2",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 11, 43, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.0003435938297472628,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 35.55555555555556,
                },
            ],
            "qubits": [1],
        },
        {
            "gate": "u3",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 11, 43, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.0006870696027746481,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 71.11111111111111,
                },
            ],
            "qubits": [1],
        },
        {
            "gate": "cz",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 15, 13, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.008932558150392844,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 241.77777777777777,
                },
            ],
            "qubits": [0, 1],
        },
        {
            "gate": "cz",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 15, 13, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.008932558150392844,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 277.3333333333333,
                },
            ],
            "qubits": [1, 0],
        },
        {
            "gate": "cz",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 15, 13, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.008932558150392844,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 277.3333333333333,
                },
            ],
            "qubits": [2, 0],
        },
        {
            "gate": "cz",
            "parameters": [
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 15, 13, tzinfo=tzutc()),
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.008932558150392844,
                },
                {
                    "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 277.3333333333333,
                },
            ],
            "qubits": [0, 2],
        },
    ],
    "general": [],
    "last_update_date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
    "qubits": [
        [
            {
                "date": datetime.datetime(2020, 5, 26, 7, 8, 55, tzinfo=tzutc()),
                "name": "T1",
                "unit": "µs",
                "value": 37.234376377678316,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 9, 44, tzinfo=tzutc()),
                "name": "T2",
                "unit": "µs",
                "value": 81.11271114086495,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                "name": "frequency",
                "unit": "GHz",
                "value": 5.2540583914546,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 8, 35, tzinfo=tzutc()),
                "name": "readout_error",
                "unit": "",
                "value": 0.014999999999999902,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 8, 35, tzinfo=tzutc()),
                "name": "prob_meas0_prep1",
                "unit": "",
                "value": 0.026666666666666616,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 8, 35, tzinfo=tzutc()),
                "name": "prob_meas1_prep0",
                "unit": "",
                "value": 0.0033333333333333335,
            },
        ],
        [
            {
                "date": datetime.datetime(2020, 5, 26, 7, 8, 55, tzinfo=tzutc()),
                "name": "T1",
                "unit": "µs",
                "value": 72.65527048705901,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 10, 14, tzinfo=tzutc()),
                "name": "T2",
                "unit": "µs",
                "value": 68.81321897253622,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 23, 26, tzinfo=tzutc()),
                "name": "frequency",
                "unit": "GHz",
                "value": 5.048728759955995,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 8, 35, tzinfo=tzutc()),
                "name": "readout_error",
                "unit": "",
                "value": 0.020000000000000018,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 8, 35, tzinfo=tzutc()),
                "name": "prob_meas0_prep1",
                "unit": "",
                "value": 0.030000000000000027,
            },
            {
                "date": datetime.datetime(2020, 5, 26, 7, 8, 35, tzinfo=tzutc()),
                "name": "prob_meas1_prep0",
                "unit": "",
                "value": 0.01,
            },
        ],
    ],
}
