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
import io
import h5py
from pathlib import Path
from tempfile import gettempdir

import pytest

from tests.utils.fixtures import load_json_fixture
from tergite.qiskit.providers.serialization import IQXJsonEncoder as PulseQobj_encoder

API_URL = "https://api.tergite.example"
QUANTUM_COMPUTER_URL = "http://loke.tergite.example"
API_TOKEN = "some-token"
BACKENDS_LIST = load_json_fixture("many_backends.json")
QOBJ_EXAMPLE = load_json_fixture("qobj_example.json")
TEST_JOB_ID = "test_job_id"
NUMBER_OF_SHOTS = 100

_BACKENDS_URL = f"{API_URL}/v2/devices"
_JOBS_URL = f"{API_URL}/jobs"
_TEST_JOB_RESULTS_URL = f"{API_URL}/jobs/{TEST_JOB_ID}"
_TEST_RESULTS_DOWNLOAD_PATH = f"{QUANTUM_COMPUTER_URL}/test_file.hdf5"
_TEST_JOB = {"job_id": TEST_JOB_ID, "upload_url": QUANTUM_COMPUTER_URL}
_HALF_NUMBER_OF_SHOTS = int(NUMBER_OF_SHOTS / 2)
_TMP_RESULTS_PATH = Path(gettempdir()) / f"{TEST_JOB_ID}.hdf5"
_TEST_CALIBRATION_URL = f"{API_URL}/v2/calibrations/Well-formed"

TEST_JOB_RESULTS = {
    "status": "DONE",
    "download_url": _TEST_RESULTS_DOWNLOAD_PATH,
    "result": {
        "memory": [
            (["0x1"] * _HALF_NUMBER_OF_SHOTS) + (["0x0"] * _HALF_NUMBER_OF_SHOTS)
        ],
    },
}
RAW_TEST_JOB_RESULTS = json.dumps(TEST_JOB_RESULTS).encode("utf-8")
GOOD_BACKEND = "Well-formed"
MALFORMED_BACKEND = "Malformed"
INVALID_API_TOKENS = ["foo", "bar", "mayo", "API_USERNAME"]

_TEST_LOGFILE_DOWNLOAD_PATH = f"{QUANTUM_COMPUTER_URL}/test_logfile.hdf5"
TEST_JOB_RESULTS_LOGFILE = {
    "job_id": TEST_JOB_ID,
    "backend": GOOD_BACKEND,
    "status": "DONE",
    "download_url": _TEST_LOGFILE_DOWNLOAD_PATH,
    "result": {
        "memory": [
            (["0x1"] * _HALF_NUMBER_OF_SHOTS) + (["0x0"] * _HALF_NUMBER_OF_SHOTS)
        ],
    },
}
TEST_CALIBRATION_RESULTS = load_json_fixture("calibrations_v2.json")


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
    # download file
    requests_mock.get(
        _TEST_RESULTS_DOWNLOAD_PATH, headers={}, content=RAW_TEST_JOB_RESULTS
    )
    requests_mock.get(_TEST_CALIBRATION_URL, headers={}, json=TEST_CALIBRATION_RESULTS)
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

    # download file
    requests_mock.get(
        _TEST_RESULTS_DOWNLOAD_PATH,
        request_headers=request_headers,
        content=RAW_TEST_JOB_RESULTS,
    )
    requests_mock.get(
        _TEST_RESULTS_DOWNLOAD_PATH, status_code=401, additional_matcher=no_auth_matcher
    )

    # # Add the missing mock for the calibration request
    requests_mock.get(
        _TEST_CALIBRATION_URL,
        request_headers=request_headers,
        json=TEST_CALIBRATION_RESULTS,
    )
    yield requests_mock


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

    with open(tergiterc_file, mode="w") as file:
        pass

    yield tergiterc_file
    tergiterc_file.unlink(missing_ok=True)


@pytest.fixture
def api_with_logfile(requests_mock, hdf5_content):
    """A mock api fixture for tests that need to use TEST_JOB_RESULTS_LOGFILE."""
    requests_mock.get(_BACKENDS_URL, headers={}, json=BACKENDS_LIST)

    # Job registration
    requests_mock.post(_JOBS_URL, headers={}, json=_TEST_JOB)
    # Job upload
    requests_mock.post(QUANTUM_COMPUTER_URL, headers={}, status_code=200)

    # Job results - use TEST_JOB_RESULTS_LOGFILE
    requests_mock.get(_TEST_JOB_RESULTS_URL, headers={}, json=TEST_JOB_RESULTS_LOGFILE)

    # Download file - use hdf5_content
    requests_mock.get(_TEST_LOGFILE_DOWNLOAD_PATH, headers={}, content=hdf5_content)

    # # Add the mock for the calibration request
    requests_mock.get(_TEST_CALIBRATION_URL, json=TEST_CALIBRATION_RESULTS)
    yield requests_mock


@pytest.fixture
def hdf5_content():
    """Create mock hdf5 content."""
    hdf5_file = io.BytesIO()
    with h5py.File(hdf5_file, "w") as hdf:
        header_group = hdf.create_group("header")
        qobj_metadata_group = header_group.create_group("qobj_metadata")
        qobj_metadata_group.attrs["shots"] = NUMBER_OF_SHOTS
        qobj_metadata_group.attrs["qobj_id"] = "test_qobj_id"
        qobj_metadata_group.attrs["num_experiments"] = 1

        qobj_data_group = header_group.create_group("qobj_data")
        QOBJ_EXAMPLE["qobj_id"] = "test_qobj_id"
        experiment_data = json.dumps(QOBJ_EXAMPLE, cls=PulseQobj_encoder, indent="\t")
        qobj_data_group.attrs["experiment_data"] = experiment_data

    hdf5_file.seek(0)
    return hdf5_file.read()


def _without_headers(headers):
    """Matches requests that don't have the given headers"""

    def matcher(request):
        for k, v in headers.items():
            if request.headers.get(k) != v:
                return True

        return False

    return matcher
