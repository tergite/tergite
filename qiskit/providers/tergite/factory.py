# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from .provider import Provider
from collections import OrderedDict
from .config import Tergiterc


class Factory:
    def __init__(self):
        self._providers = OrderedDict()
        self._tergiterc = Tergiterc()

        # get a list of provider account objects from tergiterc
        accounts_list = self._tergiterc.load_accounts()
        if not accounts_list:
            print("Warning: No stored provider account found in $HOME/.qiskit/tergiterc")

        # for each item in the accounts list create a Provider object
        for account in accounts_list:
            self._providers[account.service_name] = Provider(account)

    def use_provider_account(self, account, save=False):
        if save:
            self._tergiterc.save_accounts([account])

        new_provider = Provider(account)
        self._providers[account.service_name] = new_provider

        return new_provider

    def providers(self):
        return list(self._providers.keys())

    def get_provider(self, service_name=None):
        providers = self._providers

        if not providers:
            raise Exception("No provider account is available. Provide one via Tergite.use_provider_account(..).")

        # get by name or default to the first entry
        return providers.get(service_name, next(iter(providers.values())))
