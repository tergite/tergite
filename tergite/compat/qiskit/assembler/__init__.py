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
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
========================================================
Circuit and Schedule Assembler (:mod:`qiskit.assembler`)
========================================================

.. currentmodule:: qiskit.assembler

Functions
=========


.. autofunction:: assemble_circuits

.. autofunction:: assemble_schedules

.. autofunction:: disassemble

Classes
=======

.. autosummary::
   :toctree: ../stubs/

   RunConfig
"""

from .assemble_circuits import assemble_circuits
from .assemble_schedules import assemble_schedules
from .disassemble import disassemble
from .run_config import RunConfig
