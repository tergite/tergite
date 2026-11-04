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

import httpx
import respx


@dataclasses.dataclass
class MockRequest:
    url: str
    method: str
    json: Optional[Dict[str, Any]] = None
    has_text: bool = False

    @classmethod
    def load(cls, req: httpx.Request) -> "MockRequest":
        json_data = None
        try:
            json_data = json.loads(req.content)
        except (TypeError, ValueError):
            pass

        return cls(
            url=str(req.url),
            method=req.method,
            json=json_data,
            has_text=bool(req.content),
        )


def get_request_list(router: respx.MockRouter) -> List[MockRequest]:
    """Retrieves the list of requests the mocked API received

    Args:
        router: the router of the mocked API

    Returns:
        the list of MockRequest made
    """

    return [MockRequest.load(call.request) for call in router.calls]
