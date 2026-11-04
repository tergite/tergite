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
"""Test utilities for the job files the SDK uploads to the mocked backends"""

from email.parser import BytesParser
from email.policy import default as default_policy

import httpx
import respx

from tergite.clients.bcc.models import JobFile


def get_uploaded_job_file(router: respx.MockRouter) -> JobFile:
    """Gets the job file of the last job uploaded to a mocked backend

    Args:
        router: the router of the mocked API

    Returns:
        the job file, as the backend reads it
    """
    upload = next(
        call.request
        for call in reversed(router.calls)
        if call.request.method == "POST" and call.request.url.path.endswith("/jobs")
    )
    return JobFile.model_validate_json(_get_upload_file(upload))


def _get_upload_file(request: httpx.Request) -> bytes:
    """The bytes of the multipart request's upload_file field"""
    message = BytesParser(policy=default_policy).parsebytes(
        b"Content-Type: "
        + request.headers["Content-Type"].encode("utf-8")
        + b"\r\nMIME-Version: 1.0\r\n\r\n"
        + request.content
    )
    for part in message.iter_parts():
        params = dict(part.get_params(header="content-disposition", unquote=True))
        if params.get("name") == "upload_file":
            return part.get_payload(decode=True)
    raise AssertionError("the upload has no upload_file field")
