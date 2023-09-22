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
"""Handles the loading and saving of configuration to tergiterc file"""
import pathlib
import re
from configparser import ConfigParser
from typing import List, Optional

from .provider_account import ProviderAccount

TERGITERC_FILE = pathlib.Path.home() / ".qiskit" / "tergiterc"

REST_API_MAP = {
    "jobs": "/jobs",
    "result": "/result",
    "download_url": "/download_url",
    "calibrations": "/calibrations",
    "backends": "/backends",
}


class Tergiterc:
    """the Configuration parser for tergiterc files"""

    def __init__(self):
        """Initializes a Tergiterc instance

        The instance initialized, saves to and retrieves its
        data from ``$HOME/.qiskit/tergiterc``
        """
        self._parser = Tergiterc._get_parser()

    def load_accounts(self) -> List["ProviderAccount"]:
        """Retrieves the accounts from the tergiterc file

        Returns:
            list of instances of
                :class:`~tergite_qiskit_connector.providers.tergite.provider_account.ProviderAccount`
                as read from the tergiterc file
        """
        accounts = []

        parser = self._parser
        if not parser:
            return accounts

        sections_all = parser.sections()
        for section in sections_all:
            if section.startswith("service"):
                if not parser.has_option(section, "url"):
                    print(
                        f"Warning: Skipping account provider '{section}'. Invalid configuration."
                    )
                    continue

                section_items = dict(parser.items(section))
                service_name = section.split(" ", 1)[1].strip()
                new_account = ProviderAccount(service_name, **section_items)
                accounts.append(new_account)

        return accounts

    def save_accounts(self, accounts: List["ProviderAccount"]):
        """Saves the accounts into the tergiterc file

        Args:
            accounts: the list of instances of
                :class:`~tergite_qiskit_connector.providers.tergite.provider_account.ProviderAccount`
                to save

        Raises:
            Exception: If no accounts are passed
        """
        if not accounts:
            raise Exception("Cannot save account(s). None given.")

        if not self._parser:
            self._parser = ConfigParser()

        for account in accounts:
            # section
            section_name = "service " + account.service_name
            self._parser.add_section(section_name)

            # account configuration
            config = account.to_dict()
            config.update(config.pop("extras"))  # flatten on 'extras'
            config.pop("service_name")  # remove 'service_name'

            for key, value in config.items():
                self._parser.set(section_name, str(key), str(value))

        with TERGITERC_FILE.open("w") as dest:
            self._parser.write(dest)

    @staticmethod
    def _get_parser() -> Optional[ConfigParser]:
        """Initializes a :class:`configparser.ConfigParser` instance that
        has read from ``$HOME/.qiskit/tergiterc``

        It returns None if ``$HOME/.qiskit/tergiterc`` does not exist.

        Returns:
            Optional[configparser.ConfigParser]: the ConfigParser with the
                ``$HOME/.qiskit/tergiterc`` loaded in it if the
                file does not exist
        """
        if not TERGITERC_FILE.exists():
            return None

        parser = ConfigParser()
        parser.SECTCRE = re.compile(r"\[ *(?P<header>[^]]+?) *\]")
        parser.read(TERGITERC_FILE)

        return parser
