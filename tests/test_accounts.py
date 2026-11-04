# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""Tests of loading and saving the accounts in the rc file"""

import os
import stat
import warnings

import pytest

from tergite.providers.accounts import (
    Account,
    get_environment_account,
    load_accounts,
    save_account,
)

_POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="Windows has no file modes")


def test_load_accounts_of_a_missing_file(tmp_path):
    """A missing rc file holds no accounts"""
    assert load_accounts(tmp_path / "tergiterc") == []


def test_load_accounts_with_padded_section_names(tmp_path):
    """Spaces inside a section's brackets are not part of the service's name"""
    rc_file = tmp_path / "tergiterc"
    rc_file.write_text("[ service foo ]\nurl = http://foo.example\ntoken = t\n")
    rc_file.chmod(0o600)

    assert load_accounts(rc_file) == [Account("foo", "http://foo.example", "t")]


def test_save_account_keeps_the_other_accounts(tmp_path):
    """Saving an account leaves those of other names as they were, in their order"""
    rc_file = tmp_path / "tergiterc"
    save_account(rc_file, Account("foo", "http://foo.example"))
    save_account(rc_file, Account("bar", "http://bar.example", "t"))
    save_account(rc_file, Account("foo", "http://new.example"))

    assert load_accounts(rc_file) == [
        Account("foo", "http://new.example"),
        Account("bar", "http://bar.example", "t"),
    ]


def test_save_account_with_percent_signs(tmp_path):
    """A '%' in a URL or token is saved and read back as it is"""
    rc_file = tmp_path / "tergiterc"
    account = Account("foo", "http://foo.example/a%20b", "to%ken")

    save_account(rc_file, account)

    assert load_accounts(rc_file) == [account]


@_POSIX_ONLY
def test_save_account_makes_the_file_and_folder_their_owners_alone(tmp_path):
    """A new rc file is readable by its owner alone, and so is a folder made for it"""
    rc_file = tmp_path / ".qiskit" / "tergiterc"

    save_account(rc_file, Account("foo", "http://foo.example", "t"))

    assert stat.S_IMODE(rc_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(rc_file.parent.stat().st_mode) == 0o700


@_POSIX_ONLY
def test_save_account_makes_an_existing_file_its_owners_alone(tmp_path):
    """An rc file others could read, as earlier releases saved it, is its owner's alone
    once an account is saved into it"""
    rc_file = tmp_path / "tergiterc"
    rc_file.write_text("[service foo]\nurl = http://foo.example\n")
    rc_file.chmod(0o644)

    save_account(rc_file, Account("bar", "http://bar.example", "t"))

    assert stat.S_IMODE(rc_file.stat().st_mode) == 0o600


@_POSIX_ONLY
def test_load_accounts_warns_of_a_file_others_can_read(tmp_path):
    """Loading an rc file its group or other users can read warns how to make it private"""
    rc_file = tmp_path / "tergiterc"
    rc_file.write_text("[service foo]\nurl = http://foo.example\n")
    rc_file.chmod(0o640)

    with pytest.warns(
        UserWarning, match=f"make it yours alone with: chmod 600 {rc_file}"
    ):
        accounts = load_accounts(rc_file)

    assert accounts == [Account("foo", "http://foo.example")]


def test_load_accounts_of_a_private_file_is_silent(tmp_path):
    """Loading an rc file saved by save_account warns of nothing"""
    rc_file = tmp_path / "tergiterc"
    save_account(rc_file, Account("foo", "http://foo.example"))

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        load_accounts(rc_file)


@pytest.mark.parametrize(
    "environ, expected",
    [
        (
            {"TERGITE_API_URL": "http://foo.example", "TERGITE_API_TOKEN": "t"},
            Account("env", "http://foo.example", "t"),
        ),
        (
            {"TERGITE_API_URL": "http://foo.example"},
            Account("env", "http://foo.example"),
        ),
        ({"TERGITE_API_TOKEN": "t"}, None),
        ({}, None),
    ],
    ids=["url-and-token", "url-alone", "token-alone", "neither"],
)
def test_get_environment_account(environ, expected):
    """The environment sets the account named env when it sets a URL"""
    assert get_environment_account(environ) == expected
