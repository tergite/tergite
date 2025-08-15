from collections.abc import Iterable

from qiskit.circuit import QuantumCircuit


def as_circuit_list(experiments):
    """Always return a list of QuantumCircuit objects."""
    if isinstance(experiments, QuantumCircuit):
        return [experiments]
    if isinstance(experiments, Iterable):
        return list(experiments)
    raise TypeError("experiments must be a QuantumCircuit or iterable")


def normalise_classical_registers(
    qc: QuantumCircuit, /, *, prefer_c: bool
) -> QuantumCircuit:
    """
    Return `qc` with at most one classical register.
    By default when you initialize QuantumCircuit in Qiskit i.e. with QuantumCircuit(2, 2).
    It would create classical register named 'c'. Which you can access with measure(qbit, cbit).
    However, when you do measurements through measure_all() - it would create a different register 'meas'.
    To avoid index errors on backend where measurements are send back to SDK with meas_maps, we need to delete
    one of the registers that is not used.

    • If `prefer_c` is True and a classical register named 'c' exists and has the
      required length, measurements are rewritten to target that register
      and every unused register is dropped.

    • Otherwise (or if 'c' is unusable), any register that contains no
      measured bits is removed; the remaining register(s) stay unchanged.

    The function never deletes a register that holds at least one bit
    referenced in an instruction, so partial-measurement circuits are
    preserved as-is.
    """
    # classifying the existing registers
    # used bits are the ones we can find in the instructions
    used_bits = {cb for inst in qc.data for cb in inst.clbits}

    # it is assumed that a circuit does at least one measurement
    # we can then filter a creg that has at least one bit used
    reg_used = {creg: any(cb in used_bits for cb in creg) for creg in qc.cregs}

    # early exit – nothing to rewrite or delete
    if sum(reg_used.values()) == 1 and all(reg_used.values()):
        return qc

    # decide which register we want to keep
    keep_creg = None
    if prefer_c:
        for creg in qc.cregs:
            if creg.name == "c" and len(creg) >= len(used_bits):
                keep_creg = creg
                break
    if keep_creg is None:
        # keep the first register that actually contains a measurement
        keep_creg = next(creg for creg, used in reg_used.items() if used)

    # build a cleaned‑up circuit
    qc_new = QuantumCircuit(qc.num_qubits)
    qc_new.add_register(keep_creg)

    # mapping old clbit → new clbit (only for bits that are used)
    bit_map = {
        cb: keep_creg[i]
        for i, cb in enumerate(
            sorted(used_bits, key=lambda x: (x._register.name, x._index))
        )
    }

    # copy/rewrite every instruction
    for inst in qc.data:
        new_cargs = [bit_map[cb] for cb in inst.clbits]
        qc_new.append(inst.operation, inst.qubits, new_cargs)

    qc_new.global_phase = qc.global_phase
    qc_new.metadata = getattr(qc, "metadata", None)
    qc_new.name = getattr(qc, "name", None)
    return qc_new
