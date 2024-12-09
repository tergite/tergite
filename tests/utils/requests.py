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
"""Utilities for handling mock requests in tests"""
import dataclasses
import json
from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class MockRequest:
    url: str
    method: str
    json: Optional[Dict[str, Any]] = None
    has_text: bool = False

    @classmethod
    def load(cls, req):
        json_data = None
        try:
            json_data = req.json()
        except (AttributeError, TypeError, json.JSONDecodeError):
            pass

        return cls(
            url=req.url,
            method=req.method,
            json=json_data,
            has_text=(req.text is not None),
        )


def get_request_list(requests_mocker) -> List[MockRequest]:
    """Retrieves the list of requests from the requests_mocker.

    Args:
        requests_mocker: the Mock object from requests_mock

    Returns:
        the list of MockRequest made
    """

    return [MockRequest.load(v) for v in requests_mocker.request_history]
