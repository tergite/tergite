import re
from datetime import datetime

import pytest

from tergite.qiskit.providers import factory, provider_account
from tests.utils.env import is_end_to_end
from tests.utils.fixtures import load_json_fixture

_PROVIDER_ACCOUNTS = load_json_fixture("provider_accounts.json")


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_use_provider_account(account_data, mock_tergiterc):
    """use_provider_account without save option returns the given provider account"""
    account = provider_account.ProviderAccount(**account_data)
    _tergite = factory.Factory(rc_file=mock_tergiterc)
    provider = _tergite.use_provider_account(account)
    assert provider.provider_account == account


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
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

    account = provider_account.ProviderAccount(**account_data)
    _tergite = factory.Factory(rc_file=mock_tergiterc)
    provider = _tergite.use_provider_account(account, save=True)
    with open(mock_tergiterc, "r") as file:
        actual_config = file.read()

    assert expected_config in actual_config
    assert provider.provider_account == account


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_get_provider(account_data, mock_tergiterc):
    """get_provider returns the provider with the given service name"""
    account = provider_account.ProviderAccount(**account_data)
    _tergite = factory.Factory(rc_file=mock_tergiterc)
    expected = _tergite.use_provider_account(account, save=True)
    got = _tergite.get_provider(account.service_name)
    assert got == expected


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_get_provider_non_existing(account_data, mock_tergiterc):
    """get_provider for non-existing service returns first provider"""
    account = provider_account.ProviderAccount(**account_data)
    _tergite = factory.Factory(rc_file=mock_tergiterc)
    _tergite.use_provider_account(account, save=True)
    provider = _tergite.get_provider(datetime.now().isoformat())

    with open(mock_tergiterc, "r") as file:
        conf = file.read()

    first_service_name = re.search(r"\[service\s+(.+?)]\n", conf).group(1)
    assert provider.provider_account.service_name == first_service_name
