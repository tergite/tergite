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
=============================================
Compilation Routines (:mod:`qiskit.compiler`)
=============================================

.. currentmodule:: qiskit.compiler

Circuit and Pulse Compilation Functions
=======================================

.. autofunction:: assemble
.. autofunction:: schedule
.. autofunction:: transpile
.. autofunction:: sequence

"""

from .assembler import assemble
from qiskit.compiler.transpiler import transpile
from qiskit.compiler.scheduler import schedule
from qiskit.compiler.sequencer import sequence
