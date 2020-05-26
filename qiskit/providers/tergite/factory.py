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

from .provider import Provider


class Factory:
    def __init__(self):
        self._providers = [Provider()]  # creates an instance of Tergite Provider
        print("Tergite: Factory init called")

    def providers(self):
        return self._providers

    def get_provider(self):
        return self._providers[0]

    status = "LOADED"
