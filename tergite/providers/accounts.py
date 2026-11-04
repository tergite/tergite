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
"""The accounts at Tergite services, as saved in the rc file or set in the environment"""

import os
import re
import stat
import warnings
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Optional

TERGITERC_FILE = Path.home() / ".qiskit" / "tergiterc"
# each account is the section "[service <name>]"; spaces may pad the brackets
SECTION_PREFIX = "service "
SECTION_REGEX = re.compile(r"\[ *(?P<header>[^]]+?) *\]")
# the file holds tokens, so it is its owner's alone, as ssh keys and ~/.netrc are
RC_FILE_MODE = 0o600
RC_FOLDER_MODE = 0o700
# as qiskit-ibm-runtime's QISKIT_IBM_URL and QISKIT_IBM_TOKEN, an account with nothing on disk
URL_ENV_VAR = "TERGITE_API_URL"
TOKEN_ENV_VAR = "TERGITE_API_TOKEN"
ENVIRONMENT_SERVICE_NAME = "env"


@dataclass
class Account:
    """An account at a Tergite service: its name, its MSS's URL, and the token for it"""

    service_name: str
    url: str
    token: Optional[str] = None


def load_accounts(rc_file: Path) -> List[Account]:
    """Loads the accounts saved in the rc file

    A section without a url is skipped with a warning, and a file other users of the
    computer can read is warned of, to be made its owner's alone.

    Args:
        rc_file: the rc file, which need not exist

    Returns:
        the accounts, in the order of the file; none if it does not exist
    """
    if _is_readable_by_others(rc_file):
        warnings.warn(
            f"The rc file {rc_file} can be read by other users of this computer; "
            f"make it yours alone with: chmod 600 {rc_file}"
        )
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


def get_environment_account(environ: Mapping[str, str]) -> Optional[Account]:
    """Gets the account the environment variables TERGITE_API_URL and TERGITE_API_TOKEN set

    Args:
        environ: the environment variables, such as os.environ

    Returns:
        the account named "env", of that URL and token, or None if no URL is set
    """
    url = environ.get(URL_ENV_VAR)
    if not url:
        return None
    return Account(
        service_name=ENVIRONMENT_SERVICE_NAME,
        url=url,
        token=environ.get(TOKEN_ENV_VAR) or None,
    )


def save_account(rc_file: Path, account: Account) -> None:
    """Saves the account into the rc file, replacing one saved under the same name

    The file and its folder are created if missing; the other accounts in it are kept, and
    each account keeps its place in the file. The file is made its owner's alone (0600), and
    a folder it creates too (0700).

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

    rc_file.parent.mkdir(mode=RC_FOLDER_MODE, parents=True, exist_ok=True)
    # created with its mode, so that no other user can read it even while it is written
    fd = os.open(rc_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, RC_FILE_MODE)
    with os.fdopen(fd, "w") as dest:
        # as the mode applies only to a file os.open creates; the file is empty by now
        os.fchmod(dest.fileno(), RC_FILE_MODE)
        parser.write(dest)


def _is_readable_by_others(rc_file: Path) -> bool:
    """Whether the rc file exists and its group or other users can read it, on systems
    whose file modes say so: Windows' do not"""
    if os.name != "posix" or not rc_file.exists():
        return False
    return bool(rc_file.stat().st_mode & (stat.S_IRGRP | stat.S_IROTH))


def _read_rc_file(rc_file: Path) -> ConfigParser:
    """The parser of the rc file, empty if the file does not exist"""
    # without interpolation, so that a '%' in a URL or token is kept as it is
    parser = ConfigParser(interpolation=None)
    parser.SECTCRE = SECTION_REGEX
    parser.read(rc_file)
    return parser
