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
import functools
import io
import json
import re
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Dict

import h5py
import pytest
import requests_mock as rq_mock
from requests import Request

from tergite.compat.qiskit.qobj.encoder import IQXJsonEncoder as PulseQobj_encoder
from tests.utils.fixtures import load_json_fixture
from tests.utils.qobj_tools import extract_uploaded_qobj_from_request

API_URL = "https://api.tergite.example"
QUANTUM_COMPUTER_URL = "http://loke.tergite.example"
API_TOKEN = "some-token"
BACKENDS_LIST = load_json_fixture("many_backends.json")
_QOBJ_RESULTS = load_json_fixture("qobj_results.json")
TEST_JOB_ID = "test_job_id"
TEST_QOBJ_ID = "test_qobj_id"
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
_JOBS_REGISTER_URL_REGEX = re.compile(f"^{API_URL}/jobs/")
_JOBS_UPLOAD_URL_REGEX = re.compile(f"^http://([\\w-]+)\.tergite\.example/jobs")
_JOBS_URL_REGEX = re.compile(f"{API_URL}/jobs/([\\w-]+)")
_JOBS_CANCEL_URL_REGEX = re.compile(
    f"^http://([\\w-]+)\.tergite\.example/jobs/([\\w-]+)/cancel"
)
_JOBS_LOGFILE_URL_REGEX = re.compile(
    r"^http://([\w-]+)\.tergite\.example/test_file.hdf5"
)

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
INVALID_API_TOKENS = ["foo", "bar", "mayo", "API_USERNAME"]

_CALIBRATIONS = load_json_fixture("calibrations.json")
TEST_CALIBRATIONS_MAP = {item["name"]: {**item} for item in _CALIBRATIONS}
TEST_QUANTUM_COMPUTER_URL_MAP = {
    backend: f"http://{backend}.tergite.example" for backend in GOOD_BACKENDS
}
TEST_LOGFILE_DOWNLOAD_MAP = {
    backend: f"http://{backend}.tergite.example/test_file.hdf5"
    for backend in GOOD_BACKENDS
}
TEST_JOBS_MAP = {
    backend: {
        "job_id": f"{TEST_JOB_ID}-{backend}",
        "upload_url": f"{TEST_QUANTUM_COMPUTER_URL_MAP[backend]}/jobs",
        "access_token": "ACCESS_TOKEN",
    }
    for backend in GOOD_BACKENDS
}
TEST_JOB_RESULTS_MAP = {
    f"{TEST_JOB_ID}-{backend}": {
        **TEST_JOB_RESULTS,
        "device": backend,
        "calibration_date": TEST_CALIBRATIONS_MAP[backend]["last_calibrated"],
        "download_url": TEST_LOGFILE_DOWNLOAD_MAP[backend],
        "access_token": "ACCESS_TOKEN",
    }
    for backend in GOOD_BACKENDS
}
TEST_QOBJ_RESULTS_MAP = {
    item["header"]["backend_name"].lower(): {**item} for item in _QOBJ_RESULTS
}


@pytest.fixture
def api(requests_mock):
    """The mock api without auth"""
    requests_mock.get(
        _BACKENDS_URL,
        headers={},
        json={"data": BACKENDS_LIST, "skip": 0, "limit": None},
    )

    # job registration
    requests_mock.post(_JOBS_URL, headers={}, json=_TEST_JOB_RESPONSE)
    # job upload
    requests_mock.post(_JOB_UPLOAD_URL, headers={}, status_code=200)
    # job details
    requests_mock.get(_TEST_JOB_URL, headers={}, json=_TEST_JOB)
    # job cancellation
    requests_mock.post(_TEST_JOB_CANCEL_URL, headers={})
    # download file
    requests_mock.get(
        _TEST_RESULTS_DOWNLOAD_PATH, headers={}, content=RAW_TEST_JOB_RESULTS
    )
    requests_mock.get(_CALIBRATIONS_REGEX, headers={}, json=_mock_calibrations_handler)
    yield requests_mock


@pytest.fixture
def bearer_auth_api(requests_mock):
    """The mock api with bearer auth"""
    mss_request_headers = {"Authorization": f"Bearer {API_TOKEN}"}
    bcc_request_headers = {"Authorization": f"Bearer ACCESS_TOKEN"}

    no_mss_auth_matcher = _without_headers(mss_request_headers)
    no_bcc_auth_matcher = _without_headers(bcc_request_headers)
    no_auth_json = {"detail": "Unauthorized"}
    requests_mock.get(
        _BACKENDS_URL,
        request_headers=mss_request_headers,
        json={"data": BACKENDS_LIST, "skip": 0, "limit": None},
    )
    requests_mock.get(
        _BACKENDS_URL,
        status_code=401,
        additional_matcher=no_mss_auth_matcher,
        json=no_auth_json,
    )

    # job registration
    requests_mock.post(
        _JOBS_URL, request_headers=mss_request_headers, json=_TEST_JOB_RESPONSE
    )
    requests_mock.post(
        _JOBS_URL,
        status_code=401,
        additional_matcher=no_mss_auth_matcher,
        json=no_auth_json,
    )

    # job upload
    requests_mock.post(
        _JOB_UPLOAD_URL, request_headers=bcc_request_headers, status_code=200
    )
    requests_mock.post(
        _JOB_UPLOAD_URL,
        status_code=401,
        additional_matcher=no_bcc_auth_matcher,
        json=no_auth_json,
    )

    # job details
    requests_mock.get(
        _TEST_JOB_URL, request_headers=mss_request_headers, json=_TEST_JOB
    )
    requests_mock.get(
        _TEST_JOB_URL,
        status_code=401,
        additional_matcher=no_mss_auth_matcher,
        json=no_auth_json,
    )

    # job cancellation
    requests_mock.post(_TEST_JOB_CANCEL_URL, headers=bcc_request_headers)
    requests_mock.post(
        _TEST_JOB_CANCEL_URL,
        status_code=401,
        additional_matcher=no_bcc_auth_matcher,
        json=no_auth_json,
    )

    # download file
    requests_mock.get(
        _TEST_RESULTS_DOWNLOAD_PATH,
        request_headers=bcc_request_headers,
        content=RAW_TEST_JOB_RESULTS,
    )
    requests_mock.get(
        _TEST_RESULTS_DOWNLOAD_PATH,
        status_code=401,
        additional_matcher=no_bcc_auth_matcher,
        json=no_auth_json,
    )

    # calibrations
    requests_mock.get(
        _CALIBRATIONS_REGEX,
        request_headers=mss_request_headers,
        json=_mock_calibrations_handler,
    )
    requests_mock.get(
        _CALIBRATIONS_REGEX,
        status_code=401,
        additional_matcher=no_mss_auth_matcher,
        json=no_auth_json,
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
def api_with_logfile(requests_mock):
    """A mock api fixture for tests that need to use TEST_JOB_RESULTS_LOGFILE."""

    # per-test state
    uploaded_qobj_by_backend: Dict[str, Any] = {}

    requests_mock.get(
        _BACKENDS_URL,
        headers={},
        json={"data": BACKENDS_LIST, "skip": 0, "limit": None},
    )

    # Job registration
    requests_mock.post(
        _JOBS_REGISTER_URL_REGEX, headers={}, json=_mock_job_registration_handler
    )

    # Job upload / captures payload
    requests_mock.post(
        _JOBS_UPLOAD_URL_REGEX,
        headers={},
        content=functools.partial(
            _mock_job_upload_handler, uploaded_qobj_by_backend=uploaded_qobj_by_backend
        ),
    )

    # Job details - use TEST_JOB_RESULTS_LOGFILE
    requests_mock.get(_JOBS_URL_REGEX, headers={}, json=_mock_job_details_handler)

    # Download file - use hdf5_content
    requests_mock.get(
        _JOBS_LOGFILE_URL_REGEX,
        headers={},
        content=functools.partial(
            _mock_logfile_download_handler_local,
            uploaded_qobj_by_backend=uploaded_qobj_by_backend,
        ),
    )

    # job cancellation
    requests_mock.post(
        _JOBS_CANCEL_URL_REGEX, headers={}, content=_mock_job_cancellation_handler
    )

    # calibration request
    requests_mock.get(_CALIBRATIONS_REGEX, json=_mock_calibrations_handler)
    yield requests_mock


def _without_headers(headers):
    """Matches requests that don't have the given headers"""

    def matcher(request):
        for k, v in headers.items():
            if request.headers.get(k) != v:
                return True

        return False

    return matcher


def _mock_calibrations_handler(request: Request, context: Any) -> Dict[str, Any]:
    """Mock API handler for v2/calibrations/{name} endpoint

    Args:
        request: the request caught
        context: the object with the extra context passed when creating mock e.g. headers

    Returns:
        the JSON data in dict form to be returned on the given endpoint
    """
    matcher = _CALIBRATIONS_REGEX.match(request.url)
    try:
        backend_name = matcher.group(1)
        data = TEST_CALIBRATIONS_MAP[backend_name]
        return {**data}
    except (AttributeError, KeyError):
        raise rq_mock.NoMockAddress(request)


def _mock_job_registration_handler(request: Request, context: Any) -> Dict[str, Any]:
    """Mock API handler for POST jobs/ MSS endpoint

    Args:
        request: the request caught
        context: the object with the extra context passed when creating mock e.g. headers

    Returns:
        the JSON data in dict form to be returned on the given endpoint
    """
    try:
        payload = request.json()
        device = payload["device"]
        data = TEST_JOBS_MAP[device]
        return {**data, **payload}
    except (AttributeError, KeyError):
        raise rq_mock.NoMockAddress(request)


def _mock_job_details_handler(request: Request, context: Any) -> Dict[str, Any]:
    """Mock API handler for GET jobs/{job_id} MSS endpoint

    Args:
        request: the request caught
        context: the object with the extra context passed when creating mock e.g. headers

    Returns:
        the JSON data in dict form to be returned on the given endpoint
    """
    matcher = _JOBS_URL_REGEX.match(request.url)
    try:
        job_id = matcher.group(1)
        data = TEST_JOB_RESULTS_MAP[job_id]
        return {**data, "job_id": job_id}
    except (AttributeError, KeyError):
        raise rq_mock.NoMockAddress(request)


def _mock_logfile_download_handler_local(
    request: Request, context: Any, uploaded_qobj_by_backend: Dict[str, Any]
):
    """
    Serve a logfile where qobj_data.experiment_data matches what was uploaded for that backend.
    Fallback to fixture qobj_results.json if nothing captured.
    """
    m = _JOBS_LOGFILE_URL_REGEX.match(request.url)
    if not m:
        raise rq_mock.NoMockAddress(request)

    backend = m.group(1).lower()

    qobj = uploaded_qobj_by_backend.get(backend)
    if qobj is None:
        raise AssertionError(f"No captured qobj upload found for backend={backend}")

    hdf5_file = io.BytesIO()
    with h5py.File(hdf5_file, "w") as hdf:
        header_group = hdf.create_group("header")
        qobj_metadata_group = header_group.create_group("qobj_metadata")

        # metadata extracted by extract_job_metadata(logfile)
        qobj_metadata_group.attrs["shots"] = qobj["config"]["shots"]
        qobj_metadata_group.attrs["qobj_id"] = qobj["qobj_id"]
        qobj_metadata_group.attrs["num_experiments"] = len(qobj["experiments"])

        # payload extracted by extract_job_qobj(logfile)
        qobj_data_group = header_group.create_group("qobj_data")
        experiment_data = json.dumps(qobj, cls=PulseQobj_encoder, indent="\t")
        qobj_data_group.attrs["experiment_data"] = experiment_data

    hdf5_file.seek(0)
    return hdf5_file.read()


def _mock_job_cancellation_handler(request: Request, context: Any):
    """Mock API handler for the job cancellation endpoint

    Args:
        request: the request caught
        context: the object with the extra context passed when creating mock e.g. headers

    Returns:
        the JSON data in dict form to be returned on the given endpoint
    """
    matcher = _JOBS_CANCEL_URL_REGEX.match(request.url)
    try:
        backend = matcher.group(1)
        job_id = matcher.group(1)
        return None
    except (AttributeError, KeyError):
        raise rq_mock.NoMockAddress(request)


def _mock_job_upload_handler(request: Request, context, uploaded_qobj_by_backend: dict):
    m = _JOBS_UPLOAD_URL_REGEX.match(request.url)
    if not m:
        raise rq_mock.NoMockAddress(request)

    backend = m.group(1).lower()
    qobj = extract_uploaded_qobj_from_request(request)

    uploaded_qobj_by_backend[backend] = qobj
    context.status_code = 200
    return b""
