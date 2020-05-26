# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

print("Tergite: __init__ start")

from .factory import Factory
from .provider import Provider
from .backend import Backend
from .job import Job
from .version import __version__

Tergite = Factory()

print("Tergite: __init__ done")
