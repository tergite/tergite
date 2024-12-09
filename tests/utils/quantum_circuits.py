# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from qiskit import QuantumCircuit
from qiskit.circuit import QuantumRegister, ClassicalRegister


def remove_idle_qubits(circuit: QuantumCircuit) -> str:
    """
    Remove idle qubits from a QuantumCircuit.

    Parameters:
    - circuit (QuantumCircuit): The input circuit.

    Returns:
    - QuantumCircuit: A new circuit with idle qubits removed.
    """

    # Identify active qubits and classical bits
    active_qubits = set()
    active_clbits = set()
    for instr, qargs, cargs in circuit.data:
        active_qubits.update(qargs)
        active_clbits.update(cargs)

    # Map old qubits and clbits to new indices
    qubit_indices = {
        qubit: idx
        for idx, qubit in enumerate(
            sorted(active_qubits, key=lambda q: circuit.find_bit(q).index)
        )
    }
    clbit_indices = {
        clbit: idx
        for idx, clbit in enumerate(
            sorted(active_clbits, key=lambda c: circuit.find_bit(c).index)
        )
    }

    # Create new circuit with appropriate registers if they exist
    if circuit.qregs or circuit.cregs:
        # Create new registers with sizes equal to the number of active bits
        qregs = [QuantumRegister(len(active_qubits), name="q")]
        cregs = [ClassicalRegister(len(active_clbits), name="c")]
        new_circuit = QuantumCircuit(
            *qregs, *cregs, name=circuit.name, global_phase=circuit.global_phase
        )

    # Copy calibrations if present
    if hasattr(circuit, "calibrations"):
        new_circuit.calibrations = circuit.calibrations.copy()

    # Reconstruct the circuit
    for instr, qargs, cargs in circuit.data:
        new_qargs = [new_circuit.qubits[qubit_indices[q]] for q in qargs]
        new_cargs = [new_circuit.clbits[clbit_indices[c]] for c in cargs]
        new_circuit.append(instr, new_qargs, new_cargs)

    # Copy circuit metadata
    new_circuit.metadata = circuit.metadata

    return new_circuit
