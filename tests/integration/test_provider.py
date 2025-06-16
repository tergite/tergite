import re
from datetime import datetime

import pytest

from tergite.services.configs import AccountInfo
from tergite.types import provider_factory as factory
from tests.utils.env import is_end_to_end
from tests.utils.fixtures import load_json_fixture

_PROVIDER_ACCOUNTS = load_json_fixture("provider_accounts.json")


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_use_provider_account(account_data, mock_tergiterc):
    """use_provider_account without save option returns the given provider account"""
    _tergite = factory.ProviderFactory(rc_file=mock_tergiterc)
    provider = _tergite.use_provider_account(**account_data)
    assert provider.account == AccountInfo(**account_data)


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

    _tergite = factory.ProviderFactory(rc_file=mock_tergiterc)
    provider = _tergite.use_provider_account(**account_data, save=True)
    with open(mock_tergiterc, "r") as file:
        actual_config = file.read()

    assert expected_config in actual_config
    assert provider.account == AccountInfo(**account_data)


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("account_data", _PROVIDER_ACCOUNTS)
def test_get_provider(account_data, mock_tergiterc):
    """get_provider returns the provider with the given service name"""
    _tergite = factory.ProviderFactory(rc_file=mock_tergiterc)
    expected = _tergite.use_provider_account(**account_data, save=True)
    got = _tergite.get_provider(account_data["service_name"])
    assert got == expected


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
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
