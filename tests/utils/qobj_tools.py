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
from email.parser import BytesParser
from email.policy import default as default_policy
from typing import Any

from tergite.services.api_client import JobFile


def _extract_multipart_field_bytes(
    body: bytes, content_type: str, field_name: str
) -> bytes:
    """
    Parse multipart/form-data using stdlib email, return raw bytes of the part payload
    for a given form field name (e.g. upload_file).
    """
    # email parser wants headers + body
    msg = BytesParser(policy=default_policy).parsebytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\n"
        b"MIME-Version: 1.0\r\n\r\n" + body
    )

    if not msg.is_multipart():
        raise AssertionError("Expected multipart/form-data, got non-multipart message")

    for part in msg.iter_parts():
        cd = part.get("Content-Disposition", "")
        if "form-data" not in cd:
            continue
        params = dict(part.get_params(header="content-disposition", unquote=True))
        if params.get("name") == field_name:
            return part.get_payload(decode=True) or b""

    raise AssertionError(f"Multipart field {field_name!r} not found")


def _qobj_to_dict(qobj: Any) -> dict:
    """Normalize qobj into a plain dict regardless of representation."""
    # wire format sometimes embeds qobj as JSON string
    if isinstance(qobj, str):
        qobj = json.loads(qobj)

    # pydantic model -> dict (if applicable)
    if hasattr(qobj, "model_dump"):
        qobj = qobj.model_dump()

    # Tergite PulseQobj / QasmQobj objects
    if hasattr(qobj, "to_dict"):
        qobj = qobj.to_dict()

    if not isinstance(qobj, dict):
        raise AssertionError(f"qobj did not normalize to dict. type={type(qobj)}")

    return qobj


def extract_uploaded_qobj_from_request(req) -> dict:
    ct = req.headers.get("Content-Type", "")
    body = req.body
    if not isinstance(body, (bytes, bytearray)):
        raise AssertionError(
            f"Expected bytes body for multipart upload, got {type(body)}"
        )

    upload_json_bytes = _extract_multipart_field_bytes(
        bytes(body), ct, field_name="upload_file"
    )
    jobfile_dict = json.loads(upload_json_bytes.decode("utf-8"))

    jobfile = JobFile.model_validate(jobfile_dict)

    # JobFileParams is a model -> attribute access
    qobj = getattr(jobfile.params, "qobj", None)
    if qobj is None:
        # fallback if structure changes
        qobj = (jobfile_dict.get("params") or {}).get("qobj")

    qobj_dict = _qobj_to_dict(qobj)

    if not all(k in qobj_dict for k in ("config", "experiments", "qobj_id")):
        raise AssertionError(
            f"Extracted qobj dict missing keys. keys={list(qobj_dict.keys())}"
        )

    return qobj_dict
