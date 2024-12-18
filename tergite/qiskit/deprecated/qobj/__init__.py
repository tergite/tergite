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
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
#

"""
=========================
Qobj (:mod:`qiskit.qobj`)
=========================

.. currentmodule:: qiskit.qobj

Base
====

.. autosummary::
   :toctree: ../stubs/

   QobjExperimentHeader
   QobjHeader

Qasm
====

.. autosummary::
   :toctree: ../stubs/

   QasmQobj
   QasmQobjInstruction
   QasmQobjExperimentConfig
   QasmQobjExperiment
   QasmQobjConfig
   QasmExperimentCalibrations
   GateCalibration

Pulse
=====

.. autosummary::
   :toctree: ../stubs/

   PulseQobj
   PulseQobjInstruction
   PulseQobjExperimentConfig
   PulseQobjExperiment
   PulseQobjConfig
   QobjMeasurementOption
   PulseLibraryItem
"""

from tergite.qiskit.deprecated.qobj.common import QobjExperimentHeader, QobjHeader
from tergite.qiskit.deprecated.qobj.pulse_qobj import (
    PulseLibraryItem,
    PulseQobj,
    PulseQobjConfig,
    PulseQobjExperiment,
    PulseQobjExperimentConfig,
    PulseQobjInstruction,
    QobjMeasurementOption,
)
from tergite.qiskit.deprecated.qobj.qasm_qobj import (
    GateCalibration,
    QasmExperimentCalibrations,
    QasmQobj,
    QasmQobjConfig,
    QasmQobjExperiment,
    QasmQobjExperimentConfig,
    QasmQobjInstruction,
)
