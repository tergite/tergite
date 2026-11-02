# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
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
# Chalmers Next Labs, 2025, 2026
"""The accounts at Tergite services, as saved in the rc file"""
import re
import warnings
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

TERGITERC_FILE = Path.home() / ".qiskit" / "tergiterc"
# each account is the section "[service <name>]"; spaces may pad the brackets
SECTION_PREFIX = "service "
SECTION_REGEX = re.compile(r"\[ *(?P<header>[^]]+?) *\]")


@dataclass
class Account:
    """An account at a Tergite service: its name, its MSS's URL, and the token for it"""

    service_name: str
    url: str
    token: Optional[str] = None


def load_accounts(rc_file: Path) -> List[Account]:
    """Loads the accounts saved in the rc file

    A section without a url is skipped with a warning.

    Args:
        rc_file: the rc file, which need not exist

    Returns:
        the accounts, in the order of the file; none if it does not exist
    """
    parser = _read_rc_file(rc_file)
    accounts = []
    for section in parser.sections():
        if not section.startswith(SECTION_PREFIX):
            continue
        if not parser.has_option(section, "url"):
            warnings.warn(
                f"Skipping account provider '{section}'. Invalid configuration."
            )
            continue
        accounts.append(
            Account(
                service_name=section.removeprefix(SECTION_PREFIX).strip(),
                url=parser.get(section, "url"),
                token=parser.get(section, "token", fallback=None),
            )
        )
    return accounts


def save_account(rc_file: Path, account: Account) -> None:
    """Saves the account into the rc file, replacing one saved under the same name

    The file and its folder are created if missing; the other accounts in it are kept, and
    each account keeps its place in the file.

    Args:
        rc_file: the rc file
        account: the account to save
    """
    parser = _read_rc_file(rc_file)
    values = {"url": account.url}
    # a None would be written as "None" and read back as that string
    if account.token is not None:
        values["token"] = account.token
    # replaces the section's values where it is, so the accounts keep their order
    parser[SECTION_PREFIX + account.service_name] = values

    rc_file.parent.mkdir(parents=True, exist_ok=True)
    with rc_file.open("w") as dest:
        parser.write(dest)


def _read_rc_file(rc_file: Path) -> ConfigParser:
    """The parser of the rc file, empty if the file does not exist"""
    # without interpolation, so that a '%' in a URL or token is kept as it is
    parser = ConfigParser(interpolation=None)
    parser.SECTCRE = SECTION_REGEX
    parser.read(rc_file)
    return parser
