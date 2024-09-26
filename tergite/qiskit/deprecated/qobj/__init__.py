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
# This code is part of Tergite
#
# (C) Adilet Tuleuov 2024
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
# This code was modified on September 23, 2023 by Adilet Tuleuov
# Import statements were adjusted to isolate deprecated packages from qiskit package. 
# The reason is to suppport existing functionality that is to be removed from qiskit package. 

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

from tergite.qiskit.deprecated.qobj.common import QobjExperimentHeader
from tergite.qiskit.deprecated.qobj.common import QobjHeader

from tergite.qiskit.deprecated.qobj.pulse_qobj import PulseQobj
from tergite.qiskit.deprecated.qobj.pulse_qobj import PulseQobjInstruction
from tergite.qiskit.deprecated.qobj.pulse_qobj import PulseQobjExperimentConfig
from tergite.qiskit.deprecated.qobj.pulse_qobj import PulseQobjExperiment
from tergite.qiskit.deprecated.qobj.pulse_qobj import PulseQobjConfig
from tergite.qiskit.deprecated.qobj.pulse_qobj import QobjMeasurementOption
from tergite.qiskit.deprecated.qobj.pulse_qobj import PulseLibraryItem

from tergite.qiskit.deprecated.qobj.qasm_qobj import GateCalibration
from tergite.qiskit.deprecated.qobj.qasm_qobj import QasmExperimentCalibrations
from tergite.qiskit.deprecated.qobj.qasm_qobj import QasmQobj
from tergite.qiskit.deprecated.qobj.qasm_qobj import QasmQobjInstruction
from tergite.qiskit.deprecated.qobj.qasm_qobj import QasmQobjExperiment
from tergite.qiskit.deprecated.qobj.qasm_qobj import QasmQobjConfig
from tergite.qiskit.deprecated.qobj.qasm_qobj import QasmQobjExperimentConfig
