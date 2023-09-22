# This code is part of Tergite
#
# (C) Copyright Axel Andersson 2022
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
"""Handles the calibration of the devices of type OpenPulseBackend"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd
import qiskit.circuit as circuit
import requests
from qiskit.transpiler import InstructionProperties, Target

from . import template_schedules as templates
from .config import REST_API_MAP

if TYPE_CHECKING:
    from .backend import OpenPulseBackend


# TODO: Replace with BCC graph node
@dataclass(frozen=True)
class Node:
    """Parsing node for job objects from the API

    Note: the keys in the job objects should be
    valid Python string identifiers

    This node transforms the keys in the job object
    into attributes

    Attributes:
        data: the data to instantiate the node with
    """
    data: dict

    def __post_init__(self):
        # subvert frozen restriction, create new frozen fields for key value pairs in data
        for k, v in self.data.items():
            object.__setattr__(self, k, v)

    def __repr__(self) -> str:
        return self.job_id


def load_tables(*, backend: "OpenPulseBackend") -> tuple:
    """Parses the job_id calibration tables got from the API.

    Each job_id in the cells is parsed into a "calibration node".

    A calibration node corresponds to a document in the calibrations/
    column in MongoDB. The fields of calibration nodes correspond
    to the top-level keys of the calibration document.

    For example, if there is a job_id in the qubit calibration table
    with job_id = "ad9c9e3d-c05e-4a9f-a45f-6ee9a3be5f24" and there is
    also a document in the calibrations/ column with the following
    structure:
    {
      "job_id": "ad9c9e3d-c05e-4a9f-a45f-6ee9a3be5f24",
      "type": "qubit_calibrations",
      "name": "qubit_spectroscopy",
      "frequency": 3749584708.1745853,
      "timelog": {
        "REGISTERED": "2022-10-26T07:07:07.347Z"
      }
    }
    Then, there will be a calibration node X in the qubit calibration table
    with: X.job_id = "ad9c9e3d-c05e-4a9f-a45f-6ee9a3be5f24"
          X.name = "qubit_spectroscopy"
          X.frequency = 3749584708.1745853
          ...
          etc.

    Args:
        backend: the instance of
            :class:`~tergite_qiskit_connector.providers.tergite.backend:TergiteBackend`
            from which the calibration tables are to be loaded.

    Returns:
        A (Q, R, C) tuple of pandas DataFrames Q, R, and C where
            Q contains the calibration nodes for all the qubit devices.
            R contains the calibration nodes for all the resonator devices.
            C contains the calibration nodes for all the coupler devices.
    """

    def _load_and_index(data_index_key: str, data_table_key: str):
        # helper function for loading dataframe
        df = pd.DataFrame(data=backend.data[data_table_key])

        ind_colname = data_index_key.split("num_")[-1][:-1]
        df[ind_colname] = [i for i in range(0, backend.data[data_index_key])]
        df.set_index(ind_colname, inplace=True)
        return df

    df_qcal = _load_and_index("num_qubits", "qubit_calibrations")
    df_rcal = _load_and_index("num_resonators", "resonator_calibrations")
    df_ccal = _load_and_index("num_couplers", "coupler_calibrations")

    # FIXME: Send a single GET request to the API instead of sending multiple.
    #        Need a new API endpoint for retrieving multiple documents.
    def _convert_to_node(job_id: str):
        # Sends a get request to the API and resolves the reported job_id to calibration parameters
        calibs_url = backend.base_url + REST_API_MAP["calibrations"]
        if job_id:
            response = requests.get(calibs_url + "/" + str(job_id))
            if response.ok:
                document = response.json()
                # job_id was not found in the calibrations collection in MongoDB
                if type(document) is str:
                    raise RuntimeError(
                        f"job_id {job_id} does not have a corresponding calibration."
                    )
                else:
                    return Node(document)

            # unable to talk on the network
            else:
                raise RuntimeError(f"Unable to GET calibration parameters from MSS.")
        else:
            return None

    # parse all job_ids to calibration document nodes
    for df in (df_qcal, df_rcal, df_ccal):
        for column in df:
            df[column] = df[column].apply(_convert_to_node)

    return df_qcal, df_rcal, df_ccal


def add_instructions(*, backend: "OpenPulseBackend", qubits: tuple, target: Target):
    """Adds Rx, Rz gates and Delay and Measure instructions for each qubit
    to the transpiler target provided.

    Implementations are backend dependent and are based on a specific calibration.

    Args:
        backend: the instance of
            :class:`~tergite_qiskit_connector.providers.tergite.backend:TergiteBackend`
            for which to add the instructions
        qubits: a tuple of qubits on which the instruction is to be run
        target: the target on which the instruction is to be added
    """
    # TODO: Fetch error statistics of gates from database

    rx_theta = circuit.Parameter("theta")
    rz_lambda = circuit.Parameter("lambda")
    delay_tau = circuit.Parameter("tau")

    # Reset qubits to ground state
    reset_props = {
        (q,): InstructionProperties(
            error=0.0,
            calibration=templates.delay(backend, (q,), 300 * 1000, delay_str="Reset"),
        )
        for q in qubits
    }
    target.add_instruction(circuit.library.Reset(), reset_props)

    # Rotation around X-axis on Bloch sphere
    rx_props = {
        (q,): InstructionProperties(
            error=0.0, calibration=templates.rx(backend, (q,), rx_theta)
        )
        for q in qubits
    }
    target.add_instruction(circuit.library.standard_gates.RXGate(rx_theta), rx_props)

    # Rotation around Z-axis on Bloch sphere
    rz_props = {
        (q,): InstructionProperties(
            error=0.0, calibration=templates.rz(backend, (q,), rz_lambda)
        )
        for q in qubits
    }
    target.add_instruction(circuit.library.standard_gates.RZGate(rz_lambda), rz_props)

    # Delay instruction
    delay_props = {
        (q,): InstructionProperties(
            error=0.0, calibration=templates.delay(backend, (q,), delay_tau)
        )
        for q in qubits
    }
    target.add_instruction(circuit.Delay(delay_tau), delay_props)

    # Measurement
    measure_props = {
        qubits: InstructionProperties(
            error=0.0, calibration=templates.measure(backend, qubits)
        )
    }
    target.add_instruction(circuit.measure.Measure(), measure_props)
