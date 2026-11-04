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
"""What the SDK's HTTP clients share: timeouts, TLS and errors"""
import functools
import ssl

import httpx

from ..exc import ApiError

# seconds before a call that sends or receives no file gives up waiting for the server
REQUEST_TIMEOUT = 30
# seconds for the calls that upload a job or download a logfile
TRANSFER_TIMEOUT = 300


def raise_for_error(response: httpx.Response, context: str) -> None:
    """Raises an ApiError for a response that is not a success

    Args:
        response: the response, read
        context: what the call was doing, which the error message starts with

    Raises:
        ApiError: {context}: {the response's detail}
    """
    if not response.is_success:
        raise ApiError(
            f"{context}: {_get_detail(response)}", status_code=response.status_code
        )


@functools.cache
def get_ssl_context() -> ssl.SSLContext:
    """Gets the SSL context every client shares: loading the CA certificates into a new one
    took a client 6.7 ms to create, against 0.06 ms with this

    Returns:
        the SSL context
    """
    return httpx.create_ssl_context()


def _get_detail(response: httpx.Response) -> str:
    """The detail of an error response, or its text if it has none"""
    try:
        return response.json()["detail"]
    except (ValueError, KeyError, TypeError):
        return response.text
