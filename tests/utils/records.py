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
