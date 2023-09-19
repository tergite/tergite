import pytest

from tests.utils.fixtures import load_json_fixture

API_URL = "https://api.tergite.example"
API_USERNAME = "admin"
API_PASSWORD = "password123"
API_TOKEN = "some-token"
BACKENDS_LIST = load_json_fixture("many_backends.json")

_BACKENDS_URL = f"{API_URL}/backends"


@pytest.fixture
def api(requests_mock):
    """The mock api without auth"""
    requests_mock.get(_BACKENDS_URL, headers={}, json=BACKENDS_LIST)
    yield requests_mock
