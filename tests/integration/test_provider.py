import os
import re
import subprocess
import sys
from datetime import datetime

import pytest

from tergite.services.configs import AccountInfo
from tergite.types import provider_factory as factory
from tests.utils.fixtures import load_json_fixture

_PROVIDER_ACCOUNTS = load_json_fixture("provider_accounts.json")


@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_use_provider_account(account_data, mock_tergiterc):
    """use_provider_account without save option returns the given provider account"""
    _tergite = factory.ProviderFactory(rc_file=mock_tergiterc)
    provider = _tergite.use_provider_account(**account_data)
    assert provider.account == AccountInfo(**account_data)


@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_use_provider_account_save(account_data, mock_tergiterc):
    """use_provider_account with save option saves the given provider account"""
    expected_config = (
        f"[service {account_data['service_name']}]\n" f"url = {account_data['url']}\n"
    )
    if "token" in account_data:
        expected_config += f"token = {account_data['token']}\n"

    extras = account_data.get("extras", {})
    for k, v in extras.items():
        expected_config += f"{k} = {v}\n"

    _tergite = factory.ProviderFactory(rc_file=mock_tergiterc)
    provider = _tergite.use_provider_account(**account_data, save=True)
    with open(mock_tergiterc, "r") as file:
        actual_config = file.read()

    assert expected_config in actual_config
    assert provider.account == AccountInfo(**account_data)


@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_get_provider(account_data, mock_tergiterc):
    """get_provider returns the provider with the given service name"""
    _tergite = factory.ProviderFactory(rc_file=mock_tergiterc)
    expected = _tergite.use_provider_account(**account_data, save=True)
    got = _tergite.get_provider(account_data["service_name"])
    assert got == expected


@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_get_provider_non_existing(account_data, mock_tergiterc):
    """get_provider for non-existing service returns first provider"""
    _tergite = factory.ProviderFactory(rc_file=mock_tergiterc)
    _tergite.use_provider_account(**account_data, save=True)
    provider = _tergite.get_provider(datetime.now().isoformat())

    with open(mock_tergiterc, "r") as file:
        conf = file.read()

    first_service_name = re.search(r"\[service\s+(.+?)]\n", conf).group(1)
    assert provider.account.service_name == first_service_name


def test_save_creates_missing_folder(tmp_path):
    """use_provider_account with save option creates the rc file's folder if missing"""
    rc_file = tmp_path / ".qiskit" / "tergiterc"
    _tergite = factory.ProviderFactory(rc_file=rc_file)
    _tergite.use_provider_account("foo", url="http://example.com", save=True)

    reloaded = factory.ProviderFactory(rc_file=rc_file)
    assert reloaded.providers() == ["foo"]


def test_save_replaces_saved_account(tmp_path):
    """use_provider_account with save option replaces an account saved under the same name"""
    rc_file = tmp_path / "tergiterc"
    _tergite = factory.ProviderFactory(rc_file=rc_file)
    _tergite.use_provider_account("foo", url="http://old.example", save=True)
    _tergite.use_provider_account("foo", url="http://new.example", save=True)

    reloaded = factory.ProviderFactory(rc_file=rc_file)
    assert reloaded.get_provider("foo").account.url == "http://new.example"


def test_save_without_token(tmp_path):
    """An account saved without a token is read back without one"""
    rc_file = tmp_path / "tergiterc"
    _tergite = factory.ProviderFactory(rc_file=rc_file)
    _tergite.use_provider_account("foo", url="http://example.com", save=True)

    reloaded = factory.ProviderFactory(rc_file=rc_file)
    assert reloaded.get_provider("foo").account.token is None


def test_import_is_silent(tmp_path):
    """Importing tergite neither reads the rc file nor prints, even when it holds an invalid account"""
    rc_file = tmp_path / ".qiskit" / "tergiterc"
    rc_file.parent.mkdir()
    rc_file.write_text("[service broken]\ntoken = some-token\n")

    completed = subprocess.run(
        [sys.executable, "-c", "import tergite"],
        env={**os.environ, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )

    assert (completed.stdout, completed.stderr) == ("", "")


def test_invalid_saved_account_warns(tmp_path):
    """A saved account without a url is skipped with a warning"""
    rc_file = tmp_path / "tergiterc"
    rc_file.write_text("[service broken]\ntoken = some-token\n")
    _tergite = factory.ProviderFactory(rc_file=rc_file)

    with pytest.warns(UserWarning, match="Skipping account provider 'service broken'"):
        assert _tergite.providers() == []
