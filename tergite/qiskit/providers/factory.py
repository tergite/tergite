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
#
# This code was refactored from the original on 22nd September, 2023 by Martin Ahindura
"""Defines the Factory class that contains multiple Tergite Providers."""
import pathlib
from collections import OrderedDict
from typing import TYPE_CHECKING, List, Optional

from .config import TERGITERC_FILE, Tergiterc
from .provider import Provider

if TYPE_CHECKING:
    from .provider_account import ProviderAccount


class Factory:
    """Container of multiple Tergite Provider's, retrievable by service name

    It can be passed a custom path to an rc file: default is `$HOME/.qiskit/tergiterc`
    """

    def __init__(self, rc_file: pathlib.Path = TERGITERC_FILE):
        self._providers = OrderedDict()
        self._tergiterc = Tergiterc(rc_file=rc_file)

        # get a list of provider account objects from tergiterc
        accounts_list = self._tergiterc.load_accounts()
        if not accounts_list:
            print(
                "Warning: No stored provider account found in $HOME/.qiskit/tergiterc"
            )

        # for each item in the accounts list create a Provider object
        for account in accounts_list:
            self._providers[account.service_name] = Provider(account)

    def use_provider_account(
        self, account: "ProviderAccount", save: bool = False
    ) -> Provider:
        """Intializes a new Provider basing on the account passed and returns it.

        Args:
            account: the instance of the
                :class:`~tergite.providers.tergite.provider_account.ProviderAccount`
                for which the provider is to be initialized
            save: whether the account should be persisted to the tergiterc file

        Returns:
            A new instance of the
                :class:`~tergite.providers.tergite.provider.Provider`
                for the given account
        """
        if save:
            self._tergiterc.save_accounts([account])

        new_provider = Provider(account)
        self._providers[account.service_name] = new_provider

        return new_provider

    def providers(self) -> List[str]:
        """Retrieves the service names of providers in this collection

        Returns:
            list of service names of providers in this collection
        """
        return list(self._providers.keys())

    def get_provider(self, service_name=None) -> Optional[Provider]:
        """Retrieves a given provider by service name

        Args:
            service_name: the name by which the given provider is saved

        Returns:
            the provider of the given service name
                if it exists or None if it doesn't
        """
        providers = self._providers

        if not providers:
            raise Exception(
                "No provider account is available. Provide one via Tergite.use_provider_account(..)."
            )

        # get by name or default to the first entry
        return providers.get(service_name, next(iter(providers.values())))
