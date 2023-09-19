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
from os import path
from typing import Any, Dict, List, Union

_TESTS_FOLDER = path.dirname(path.dirname(path.abspath(__file__)))
_FIXTURES_PATH = path.join(_TESTS_FOLDER, "fixtures")


def load_json_fixture(file_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Loads the given fixture from the fixtures directory

    Args:
        file_name: the name of the file that contains the fixture

    Returns:
        the list of dicts or the dict got from the json fixture file
    """
    fixture_path = _get_fixture_path(file_name)
    with open(fixture_path, "rb") as file:
        return json.load(file)


def _get_fixture_path(*paths: str) -> str:
    """Gets the path to the fixture

    Args:
        paths: sections of paths to the given fixture e.g. fixtures/api/rest/many_rngs.json
            would be "api", "rest", "many_rngs.json"

    Returns:
        the path to the given fixture
    """
    return path.join(_FIXTURES_PATH, *paths)
