# This code is part of Tergite
#
# (C) Chalmers Next Labs (2024)
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
# This code was modified from the original by:
# Chalmers Next Labs 2024
#
# This code is part of Qiskit.
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

"""Module providing definitions of common Qobj classes."""
from types import SimpleNamespace

from qiskit.utils import deprecate_func


class QobjDictField(SimpleNamespace):
    """A class used to represent a dictionary field in Qobj

    Exists as a backwards compatibility shim around a dictionary for Qobjs
    previously constructed using marshmallow.
    """

    @deprecate_func(
        since="1.2",
        removal_timeline="in the 2.0 release",
        additional_msg="The `Qobj` class and related functionality are part of the deprecated "
        "`BackendV1` workflow,  and no longer necessary for `BackendV2`. If a user "
        "workflow requires `Qobj` it likely relies on deprecated functionality and "
        "should be updated to use `BackendV2`.",
    )
    def __init__(self, **kwargs):
        """Instantiate a new Qobj dict field object.

        Args:
            kwargs: arbitrary keyword arguments that can be accessed as
                attributes of the object.
        """
        self.__dict__.update(kwargs)

    def to_dict(self):
        """Return a dictionary format representation of the OpenQASM 2 Qobj.

        Returns:
            dict: The dictionary form of the QobjHeader.
        """
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        """Create a new QobjHeader object from a dictionary.

        Args:
            data (dict): A dictionary representing the QobjHeader to create. It
                will be in the same format as output by :func:`to_dict`.

        Returns:
            QobjDictFieldr: The QobjDictField from the input dictionary.
        """

        return cls(**data)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.__dict__ == other.__dict__:
                return True
        return False


class QobjHeader(QobjDictField):
    """A class used to represent a dictionary header in Qobj objects."""

    pass


class QobjExperimentHeader(QobjHeader):
    """A class representing a header dictionary for a Qobj Experiment."""

    pass
