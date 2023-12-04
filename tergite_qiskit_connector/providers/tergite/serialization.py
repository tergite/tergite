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
"""Handles the serialization of job objects"""
import json
from itertools import groupby
from typing import Any, List, Tuple, Union  # , Dict

from qiskit.circuit.parameterexpression import ParameterExpression


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


# The below code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
#
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
# ---------------- ALTERATION NOTICE ---------------- #
# This code has been derived from the Qiskit json encoder in the IBMQ providers github.
# The reason is to remove IBMQ as a dependency, but still be able to use the functionality.
# It has not been altered.


class IQXJsonEncoder(json.JSONEncoder):
    """A json encoder for qobj"""

    def __encode(self, param: Any) -> Any:
        """
        Convert dictionary to contain only JSON serializable types. For example,
        if the key is a Parameter we convert it to a string.
        """
        if isinstance(param, dict):
            param_bind_str = {}
            for key in param.keys():
                value = self.__encode(param[key])

                if isinstance(key, (bool, float, int, str)) or key is None:
                    param_bind_str[key] = value
                else:
                    param_bind_str[str(key)] = value
            return param_bind_str
        elif isinstance(param, list):
            return [self.__encode(p) for p in param]
        else:
            return param

    def encode(self, o: Any) -> str:
        """
        Return a JSON string representation of a Python data structure.
        """
        new_o = self.__encode(o)
        return super().encode(new_o)

    def default(self, o: Any) -> Any:
        # Convert numpy arrays:
        if hasattr(o, "tolist"):
            return o.tolist()
        # Use Qobj complex json format:
        if isinstance(o, complex):
            return (o.real, o.imag)
        if isinstance(o, ParameterExpression):
            try:
                return float(o)
            except (TypeError, RuntimeError):
                val = complex(o)
                return val.real, val.imag
        return json.JSONEncoder.default(self, o)
