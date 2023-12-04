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
"""Utilities for handling records in tests"""
from typing import Any, Dict, List


def get_record(data: List[Dict[str, Any]], _filter: Dict[str, Any]) -> Dict[str, Any]:
    """Gets the first record in data which matches the given filter

    Args:
        data: list of records to get the record from
        _filter: partial dict that the given record should contain

    Returns:
        the first record that matches the given filter

    Raises:
        KeyError: {key}
    """
    try:
        return next(
            filter(lambda x: all([x[k] == v for k, v in _filter.items()]), data)
        )
    except StopIteration:
        raise KeyError(f"no match found for filter {_filter}")


def get_many_records(
    data: List[Dict[str, Any]], _filter: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Gets all records in data that match the given filter

    Args:
        data: list of records to get the record from
        _filter: partial dict that the given record should contain

    Returns:
        the records that match the given filter

    Raises:
        KeyError: {key}
    """
    try:
        return list(
            filter(lambda x: all([x[k] == v for k, v in _filter.items()]), data)
        )
    except IndexError:
        raise KeyError(f"no match found for filter {_filter}")
