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
"""Functionality related to the job logfile"""
import json
from itertools import groupby
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import h5py

from tergite.compat.qiskit.qobj import PulseQobj


def extract_job_metadata(logfile: Path) -> Dict[str, Any]:
    """Extracts the metadata of the job from the HDF5 logfile

    It converts any numpy types to python types

    Args:
        logfile: the path to the logfile

    Returns:
        the metadata extracted from the file at the logfile path

    Raises:
        RuntimeError: malformed logfile. '{str}' not found
    """
    with h5py.File(logfile, "r") as hdf:
        try:
            return {
                k: _np_to_py(v) for k, v in hdf["header/qobj_metadata"].attrs.items()
            }
        except KeyError as exp:
            raise RuntimeError(f"malformed logfile. '{exp}' not found")


def extract_job_qobj(logfile: Path) -> PulseQobj:
    """Extracts the PulseQobj from the HDF5 logfile

    Args:
        logfile: the path to the logfile

    Returns:
        the PulseQobj derived from the file at the logfile path

    Raises:
        RuntimeError: malformed logfile. '{str}' not found
    """
    with h5py.File(logfile, "r") as hdf:
        try:
            experiment_data = hdf["header/qobj_data"].attrs.get("experiment_data")
            return PulseQobj.from_dict(data=json.loads(experiment_data))
        except KeyError as exp:
            raise RuntimeError(f"malformed logfile. '{exp}' not found")


def _np_to_py(value: Any) -> Any:
    """Converts a potentially numpy typed value to a python inbuilt type

    Args:
        value: the value to convert

    Returns:
        the value with its python builtin type
    """
    try:
        return value.item()
    except AttributeError:
        return value


def iqx_rle(seq: List[Any]) -> List[Union[Tuple[Any], Tuple[Any, int]]]:
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
