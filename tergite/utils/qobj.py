# This code is part of Tergite
#
# (C) Copyright Axel Andersson 2022
# (C) Copyright Chalmers Next Labs 2025
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""Utility function for handling hte Qobj for a job"""
from itertools import groupby
from typing import Any, Dict, List, Optional, Tuple, Union


def compress_qobj_dict(qobj_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a compressed dictionary representation of the qobj dict

    In order to reduce the bandwidth taken up be the qobject
    dict, we do a few things with the data which will be reversed
    at the backend

    Note that this compression is in-place

    Args:
        qobj_dict: the dict of the PulseQobj to compress

    Returns:
        A compressed dict of the qobj
    """
    # In-place RLE pulse library for compression
    for pulse in qobj_dict["config"]["pulse_library"]:
        pulse["samples"] = _iqx_rle(pulse["samples"])

    return qobj_dict


def _iqx_rle(seq: List[Any]) -> List[Union[Tuple[Any], Tuple[Any, int]]]:
    """Run-length encodes a sequence.

    Constant subsequences are stored as a single term and count, rather than as the original subsequence.
    Counts equal to 1 are omitted.

    Args:
        seq: the sequence to encode

    Returns:
        A list of tuples that represent the encoding for the sequence
    """
    seq = [(k, sum(1 for _ in g)) for k, g in groupby(seq)]
    return [(c, rep) if rep > 1 else (c,) for c, rep in seq]


def derive_reg_len_from_qobj_experiment(qobj_exp) -> Optional[int]:
    """Fallback reg length from acquire memory slots."""
    mem_slots: List[int] = []
    for inst in qobj_exp.instructions:
        if getattr(inst, "name", None) != "acquire":
            continue
        ms = getattr(inst, "memory_slot", None)
        if ms is None:
            continue
        if isinstance(ms, list):
            mem_slots.extend(ms)
        else:
            mem_slots.append(int(ms))
    return (max(mem_slots) + 1) if mem_slots else None


def rewrite_acquire_memory_slots(qobj_exp, q_to_c: Dict[int, int]) -> None:
    """Rewrite acquire.memory_slot so it matches the circuit clbit indices."""
    for inst in qobj_exp.instructions:
        if getattr(inst, "name", None) != "acquire":
            continue

        qubits = getattr(inst, "qubits", None)
        mem = getattr(inst, "memory_slot", None)
        if qubits is None or mem is None:
            continue

        # Normalize to lists
        q_list = qubits if isinstance(qubits, list) else [int(qubits)]
        m_list = mem if isinstance(mem, list) else [int(mem)]

        if len(q_list) != len(m_list):
            raise ValueError("Acquire has mismatched qubits/memory_slot lengths")

        new_m_list: List[int] = []
        for q in q_list:
            if q not in q_to_c:
                raise ValueError(
                    f"Qobj metadata quantum to classical mapping doesn't have qubit {q} in {q_to_c.keys()}."
                )
            else:
                new_m_list.append(q_to_c[q])

        inst.memory_slot = new_m_list
