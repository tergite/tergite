# This code is part of Tergite
#
# (C) Copyright Martin Ahindura 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
from base64 import b64encode

import pytest

from tests.utils.fixtures import load_json_fixture

API_URL = "https://api.tergite.example"
QUANTUM_COMPUTER_URL = "http://loke.tergite.example"
API_USERNAME = "admin"
API_PASSWORD = "password123"
API_TOKEN = "some-token"
BACKENDS_LIST = load_json_fixture("many_backends.json")
TEST_JOB_ID = "test_job_id"
NUMBER_OF_SHOTS = 100

_BACKENDS_URL = f"{API_URL}/backends"
_JOBS_URL = f"{API_URL}/jobs"
_TEST_JOB_RESULTS_URL = f"{API_URL}/jobs/{TEST_JOB_ID}"
_TEST_RESULTS_FILE_PATH = f"{QUANTUM_COMPUTER_URL}/test_file.hdf5"
_TEST_JOB = {"job_id": TEST_JOB_ID, "upload_url": QUANTUM_COMPUTER_URL}
_HALF_NUMBER_OF_SHOTS = int(NUMBER_OF_SHOTS / 2)

TEST_JOB_RESULTS = {
    "status": "DONE",
    "download_url": _TEST_RESULTS_FILE_PATH,
    "result": {
        "memory": [
            (["0x1"] * _HALF_NUMBER_OF_SHOTS) + (["0x0"] * _HALF_NUMBER_OF_SHOTS)
        ],
    },
}
GOOD_BACKEND = "Well-formed"
MALFORMED_BACKEND = "Malformed"
INVALID_API_BASIC_AUTHS = [
    (
        "foo",
        "bar",
    ),
    (
        API_USERNAME,
        "bar",
    ),
    (
        "foo",
        API_PASSWORD,
    ),
    (
        "",
        API_PASSWORD,
    ),
    (
        API_USERNAME,
        "",
    ),
    (
        API_PASSWORD,
        API_USERNAME,
    ),
]
INVALID_API_TOKENS = ["foo", "bar", API_PASSWORD, API_USERNAME]


@pytest.fixture
def api(requests_mock):
    """The mock api without auth"""
    requests_mock.get(_BACKENDS_URL, headers={}, json=BACKENDS_LIST)

    # job registration
    requests_mock.post(_JOBS_URL, headers={}, json=_TEST_JOB)
    # job upload
    requests_mock.post(QUANTUM_COMPUTER_URL, headers={}, status_code=200)
    # job results
    requests_mock.get(_TEST_JOB_RESULTS_URL, headers={}, json=TEST_JOB_RESULTS)
    yield requests_mock


@pytest.fixture
def basic_auth_api(requests_mock):
    """The mock api with basic auth"""
    auth = bytearray(f"{API_USERNAME}:{API_PASSWORD}", "utf-8")
    encoded_auth = b64encode(auth).decode("ascii")
    request_headers = {"Authorization": f"Basic {encoded_auth}"}

    # mocks
    no_auth_matcher = _without_headers(request_headers)
    requests_mock.get(
        _BACKENDS_URL, json=BACKENDS_LIST, request_headers=request_headers
    )
    requests_mock.get(
        _BACKENDS_URL, status_code=401, additional_matcher=no_auth_matcher
    )

    # job registration
    requests_mock.post(_JOBS_URL, request_headers=request_headers, json=_TEST_JOB)
    requests_mock.post(_JOBS_URL, status_code=401, additional_matcher=no_auth_matcher)

    # job upload
    requests_mock.post(
        QUANTUM_COMPUTER_URL, request_headers=request_headers, status_code=200
    )
    requests_mock.post(
        QUANTUM_COMPUTER_URL, status_code=401, additional_matcher=no_auth_matcher
    )

    # job results
    requests_mock.get(
        _TEST_JOB_RESULTS_URL, request_headers=request_headers, json=TEST_JOB_RESULTS
    )
    requests_mock.get(
        _TEST_JOB_RESULTS_URL, status_code=401, additional_matcher=no_auth_matcher
    )
    yield requests_mock


@pytest.fixture
def bearer_auth_api(requests_mock):
    """The mock api with bearer auth"""
    request_headers = {"Authorization": f"Bearer {API_TOKEN}"}

    no_auth_matcher = _without_headers(request_headers)
    requests_mock.get(
        _BACKENDS_URL, request_headers=request_headers, json=BACKENDS_LIST
    )
    requests_mock.get(
        _BACKENDS_URL, status_code=401, additional_matcher=no_auth_matcher
    )

    # job registration
    requests_mock.post(_JOBS_URL, request_headers=request_headers, json=_TEST_JOB)
    requests_mock.post(_JOBS_URL, status_code=401, additional_matcher=no_auth_matcher)

    # job upload
    requests_mock.post(
        QUANTUM_COMPUTER_URL, request_headers=request_headers, status_code=200
    )
    requests_mock.post(
        QUANTUM_COMPUTER_URL, status_code=401, additional_matcher=no_auth_matcher
    )

    # job results
    requests_mock.get(
        _TEST_JOB_RESULTS_URL, request_headers=request_headers, json=TEST_JOB_RESULTS
    )
    requests_mock.get(
        _TEST_JOB_RESULTS_URL, status_code=401, additional_matcher=no_auth_matcher
    )
    yield requests_mock


def _without_headers(headers):
    """Matches requests that don't have the given headers"""

    def matcher(request):
        for k, v in headers.items():
            if request.headers.get(k) != v:
                return True

        return False

    return matcher
