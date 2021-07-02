# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2021
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


from copy import deepcopy


class ProviderAccount:
    def __init__(self, service_name, url, token=None, **kwargs):
        self.service_name = service_name
        self.url = url
        self.token = token
        self.extras = kwargs

    def to_dict(self):
        return deepcopy(vars(self))
