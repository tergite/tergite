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
from tergite.accounts import Account, load_accounts, save_account


def test_load_accounts_of_a_missing_file(tmp_path):
    """A missing rc file holds no accounts"""
    assert load_accounts(tmp_path / "tergiterc") == []


def test_load_accounts_with_padded_section_names(tmp_path):
    """Spaces inside a section's brackets are not part of the service's name"""
    rc_file = tmp_path / "tergiterc"
    rc_file.write_text("[ service foo ]\nurl = http://foo.example\ntoken = t\n")

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
