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
import json
import re
from pathlib import Path
from tempfile import gettempdir

import httpx
import pytest
import respx

from tests.utils.fixtures import load_json_fixture

API_URL = "https://api.tergite.example"
QUANTUM_COMPUTER_URL = "http://loke.tergite.example"
API_TOKEN = "some-token"
BACKENDS_LIST = load_json_fixture("many_backends.json")
TEST_JOB_ID = "test_job_id"
NUMBER_OF_SHOTS = 100

_BACKENDS_URL = f"{API_URL}/devices/"
_JOBS_URL = f"{API_URL}/jobs/"
_TEST_JOB_URL = f"{API_URL}/jobs/{TEST_JOB_ID}"
_JOB_UPLOAD_URL = f"{QUANTUM_COMPUTER_URL}/jobs"
_TEST_JOB_CANCEL_URL = f"{QUANTUM_COMPUTER_URL}/jobs/{TEST_JOB_ID}/cancel"
_TEST_RESULTS_DOWNLOAD_PATH = f"{QUANTUM_COMPUTER_URL}/test_file.hdf5"
_TEST_JOB_RESPONSE = {
    "job_id": TEST_JOB_ID,
    "upload_url": _JOB_UPLOAD_URL,
    "access_token": "ACCESS_TOKEN",
}
_HALF_NUMBER_OF_SHOTS = int(NUMBER_OF_SHOTS / 2)
_TMP_RESULTS_PATH = Path(gettempdir()) / f"{TEST_JOB_ID}.hdf5"
_CALIBRATIONS_REGEX = re.compile(f"^{API_URL}/calibrations/([\\w-]+)")

TEST_JOB_RESULTS = {
    "status": "successful",
    "download_url": _TEST_RESULTS_DOWNLOAD_PATH,
    "result": {
        "memory": [
            (["0x1"] * _HALF_NUMBER_OF_SHOTS) + (["0x0"] * _HALF_NUMBER_OF_SHOTS)
        ],
    },
}
_TEST_JOB = {
    **_TEST_JOB_RESPONSE,
    **TEST_JOB_RESULTS,
    "access_token": "ACCESS_TOKEN",
    "device": "DUMMY_DEVICE",  # a dummy device that we might be able to replace in mock handler
    "calibration_date": "DUMMY_CALIB_DATE",  # a dummy date that we might be able to replace in mock handler
}
RAW_TEST_JOB_RESULTS = json.dumps(TEST_JOB_RESULTS).encode("utf-8")
GOOD_BACKENDS = ["Well-formed", "loke", "qiskit_pulse_1q", "qiskit_pulse_2q"]
TWO_QUBIT_BACKENDS = ["Well-formed", "loke", "qiskit_pulse_2q"]
MALFORMED_BACKEND = "Malformed"
NON_PULSE_BACKEND = "OpenQASM"
INVALID_API_TOKENS = ["foo", "bar", "mayo", "API_USERNAME"]

_CALIBRATIONS = load_json_fixture("calibrations.json")
TEST_CALIBRATIONS_MAP = {item["name"]: {**item} for item in _CALIBRATIONS}


@pytest.fixture
def mocker_router():
    """The router of mocked HTTP calls, which fails a call to an unmocked URL"""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def api(mocker_router):
    """The mock api without auth"""
    mocker_router.get(_BACKENDS_URL).respond(
        json={"data": BACKENDS_LIST, "skip": 0, "limit": None}
    )
    mocker_router.post(_JOBS_URL).respond(json=_TEST_JOB_RESPONSE)
    mocker_router.post(_JOB_UPLOAD_URL).respond(200)
    mocker_router.get(_TEST_JOB_URL).respond(json=_TEST_JOB)
    mocker_router.post(_TEST_JOB_CANCEL_URL).respond(200)
    mocker_router.get(_TEST_RESULTS_DOWNLOAD_PATH).respond(content=RAW_TEST_JOB_RESULTS)
    mocker_router.get(url__regex=_CALIBRATIONS_REGEX.pattern).mock(
        side_effect=_mock_calibrations_handler
    )
    yield mocker_router


@pytest.fixture
def bearer_auth_api(mocker_router):
    """The mock api with bearer auth"""
    mss_headers = {"Authorization": f"Bearer {API_TOKEN}"}
    bcc_headers = {"Authorization": "Bearer ACCESS_TOKEN"}
    unauthorized = httpx.Response(401, json={"detail": "Unauthorized"})

    # a route with the headers answers; else the same URL's route without them refuses
    mocker_router.get(_BACKENDS_URL, headers=mss_headers).respond(
        json={"data": BACKENDS_LIST, "skip": 0, "limit": None}
    )
    mocker_router.post(_JOBS_URL, headers=mss_headers).respond(json=_TEST_JOB_RESPONSE)
    mocker_router.post(_JOB_UPLOAD_URL, headers=bcc_headers).respond(200)
    mocker_router.get(_TEST_JOB_URL, headers=mss_headers).respond(json=_TEST_JOB)
    mocker_router.post(_TEST_JOB_CANCEL_URL, headers=bcc_headers).respond(200)
    mocker_router.get(_TEST_RESULTS_DOWNLOAD_PATH, headers=bcc_headers).respond(
        content=RAW_TEST_JOB_RESULTS
    )
    mocker_router.get(url__regex=_CALIBRATIONS_REGEX.pattern, headers=mss_headers).mock(
        side_effect=_mock_calibrations_handler
    )
    for method, url in [
        ("GET", _BACKENDS_URL),
        ("POST", _JOBS_URL),
        ("POST", _JOB_UPLOAD_URL),
        ("GET", _TEST_JOB_URL),
        ("POST", _TEST_JOB_CANCEL_URL),
        ("GET", _TEST_RESULTS_DOWNLOAD_PATH),
    ]:
        mocker_router.route(method=method, url=url).mock(return_value=unauthorized)
    mocker_router.get(url__regex=_CALIBRATIONS_REGEX.pattern).mock(
        return_value=unauthorized
    )
    yield mocker_router


@pytest.fixture
def tmp_results_file():
    """The path to the tmp file where results are downloaded"""
    yield _TMP_RESULTS_PATH
    _TMP_RESULTS_PATH.unlink()


@pytest.fixture
def mock_tergiterc() -> Path:
    """The mock tergite rc file path"""
    tergiterc_file = Path(gettempdir()) / ".qiskit" / "test_tergiterc"
    tergiterc_file.parent.mkdir(parents=True, exist_ok=True)

    tergiterc_file.write_text("")
    tergiterc_file.chmod(0o600)

    yield tergiterc_file
    tergiterc_file.unlink(missing_ok=True)


def _mock_calibrations_handler(request: httpx.Request) -> httpx.Response:
    """Answers GET calibrations/{name} with the fixture calibration of the device"""
    matcher = _CALIBRATIONS_REGEX.match(str(request.url))
    data = TEST_CALIBRATIONS_MAP.get(matcher.group(1)) if matcher else None
    if data is None:
        return httpx.Response(404, json={"detail": "Not Found"})
    return httpx.Response(200, json={**data})
