# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""The errors the SDK raises"""
from typing import Optional

from qiskit.providers import QiskitBackendNotFoundError


class TergiteError(Exception):
    """The base of every error the SDK raises"""


class ApiError(TergiteError, RuntimeError):
    """MSS or a backend refused a call, or answered what the SDK cannot use

    A RuntimeError too, as the SDK raised those before it had this class.
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        """Initializes the error

        Args:
            message: what went wrong
            status_code: the HTTP status of the response, if there was one
        """
        super().__init__(message)
        self.status_code = status_code


class BackendNotFoundError(TergiteError, QiskitBackendNotFoundError):
    """No backend, or more than one, matches what was asked for

    A QiskitBackendNotFoundError too, as the SDK raised those before it had this class.
    """


class JobFailedError(TergiteError):
    """A job asked for its result failed or was cancelled"""


class UncalibratedCouplerError(TergiteError):
    """Two coupled qubits have no coupler, or no calibration of it, to make a CZ from"""
