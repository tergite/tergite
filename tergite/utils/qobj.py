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
from typing import Any, Dict, List, Tuple, Union


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
