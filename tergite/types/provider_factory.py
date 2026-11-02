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
# Alteration Notice
# -----------------
# This code was refactored from the original by:
#
# Martin Ahindura, 2023
"""Defines the ProviderFactory class that contains multiple Tergite Providers."""
from pathlib import Path
from typing import Dict, List, Optional

from ..accounts import TERGITERC_FILE, Account, load_accounts, save_account
from ..exc import TergiteError
from .provider import Provider


class ProviderFactory:
    """Container of multiple Tergite Provider's, retrievable by service name

    It can be passed a custom path to an rc file: default is `$HOME/.qiskit/tergiterc`
    """

    def __init__(self, rc_file: Path = TERGITERC_FILE):
        self._rc_file = rc_file
        self._providers: Dict[str, Provider] = {}
        self._is_loaded = False

    def use_provider_account(
        self,
        service_name: str,
        url: str,
        token: Optional[str] = None,
        save: bool = False,
    ) -> Provider:
        """Initializes a new Provider basing on the account passed and returns it.

        Args:
            service_name: the name of the service
            url: the API URL for the given service
            token: the API token to be used to connect to the service
            save: whether the account should be persisted to the tergiterc file

        Returns:
            A new instance of the
                :class:`~tergite.providers.tergite.provider.Provider`
                for the given account
        """
        self._load_saved_providers()
        account = Account(service_name=service_name, url=url, token=token)
        if save:
            save_account(self._rc_file, account)

        new_provider = Provider(account)
        self._providers[account.service_name] = new_provider

        return new_provider

    def providers(self) -> List[str]:
        """Retrieves the service names of providers in this collection

        Returns:
            list of service names of providers in this collection
        """
        self._load_saved_providers()
        return list(self._providers.keys())

    def get_provider(self, service_name=None) -> Optional[Provider]:
        """Retrieves a given provider by service name

        Args:
            service_name: the name by which the given provider is saved

        Returns:
            the provider of the given service name
                if it exists or None if it doesn't
        """
        self._load_saved_providers()
        providers = self._providers

        if not providers:
            raise TergiteError(
                "No provider account is available. Provide one via Tergite.use_provider_account(..)."
            )

        # get by name or default to the first entry
        return providers.get(service_name, next(iter(providers.values())))

    def _load_saved_providers(self) -> None:
        """Loads the providers saved in the rc file, on the first call only"""
        if not self._is_loaded:
            self._is_loaded = True
            for account in load_accounts(self._rc_file):
                self._providers[account.service_name] = Provider(account)
