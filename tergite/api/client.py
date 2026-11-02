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
"""The HTTP clients the SDK talks to MSS and the backends with"""
import functools
import ssl
from typing import Callable, Optional

import httpx

from ..exc import ApiError

# seconds before a call that sends or receives no file gives up waiting for the server
REQUEST_TIMEOUT = 30
# seconds for the calls that upload a job or download a logfile
TRANSFER_TIMEOUT = 300


def create_mss_client(url: str, get_token: Callable[[], Optional[str]]) -> httpx.Client:
    """Creates the client of an MSS, authenticated with the account's app token

    Args:
        url: the root URL of MSS
        get_token: gets the app token, or None for an MSS that asks for none; it is
            called for each request, so that a token changed on the account is used

    Returns:
        the client, whose paths are relative to MSS's root URL
    """

    def authenticate(request: httpx.Request) -> httpx.Request:
        token = get_token()
        if token is not None:
            request.headers["Authorization"] = f"Bearer {token}"
        return request

    return httpx.Client(
        base_url=url,
        auth=authenticate,
        timeout=REQUEST_TIMEOUT,
        verify=_get_ssl_context(),
    )


def create_bcc_client() -> httpx.Client:
    """Creates the client of the backends, which each job gives its URL and token

    Returns:
        the client
    """
    return httpx.Client(timeout=REQUEST_TIMEOUT, verify=_get_ssl_context())


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


def _get_detail(response: httpx.Response) -> str:
    """The detail of an error response, or its text if it has none"""
    try:
        return response.json()["detail"]
    except (ValueError, KeyError, TypeError):
        return response.text


@functools.cache
def _get_ssl_context() -> ssl.SSLContext:
    """The SSL context every client shares: loading the CA certificates into a new one
    took a client 6.7 ms to create, against 0.06 ms with this"""
    return httpx.create_ssl_context()
