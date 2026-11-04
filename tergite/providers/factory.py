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

import os
from pathlib import Path
from typing import Dict, List, Optional

from ..exc import TergiteError
from .accounts import (
    TERGITERC_FILE,
    Account,
    get_environment_account,
    load_accounts,
    save_account,
)
from .provider import Provider


class ProviderFactory:
    """Container of multiple Tergite Provider's, retrievable by service name

    It can be passed a custom path to an rc file: default is `$HOME/.qiskit/tergiterc`. On
    first use, it loads the accounts saved there and, ahead of them, the account named "env"
    that the environment variables TERGITE_API_URL and TERGITE_API_TOKEN set, if any.
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
        self._load_providers()
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
        self._load_providers()
        return list(self._providers.keys())

    def get_provider(self, service_name: Optional[str] = None) -> Provider:
        """Gets the provider of the given service name, or the first if none is given

        Args:
            service_name: the name the provider's account is saved or used under, or "env"
                for the environment's

        Returns:
            the provider of that name, or, if no name is given, the environment's account's
            if TERGITE_API_URL is set, else that of the first account saved or used

        Raises:
            TergiteError: No provider account is available. Provide one via
                Tergite.use_provider_account(..) or TERGITE_API_URL and TERGITE_API_TOKEN.
            TergiteError: No provider account is named '{service_name}'; there are: {names}
        """
        self._load_providers()
        providers = self._providers

        if not providers:
            raise TergiteError(
                "No provider account is available. Provide one via Tergite.use_provider_account(..) "
                "or TERGITE_API_URL and TERGITE_API_TOKEN."
            )
        if service_name is None:
            return next(iter(providers.values()))
        if service_name not in providers:
            raise TergiteError(
                f"No provider account is named '{service_name}'; there are: "
                f"{', '.join(providers)}"
            )
        return providers[service_name]

    def _load_providers(self) -> None:
        """Loads the providers of the environment's account and of the saved accounts, the
        environment's first and in place of a saved one of its name, on the first call only
        """
        if self._is_loaded:
            return
        self._is_loaded = True
        environment_account = get_environment_account(os.environ)
        if environment_account is not None:
            self._providers[environment_account.service_name] = Provider(
                environment_account
            )
        for account in load_accounts(self._rc_file):
            if account.service_name not in self._providers:
                self._providers[account.service_name] = Provider(account)
