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
"""Checks that a running service serves schemas compatible with the SDK's pinned copy of its spec

Usage: python -m dev.openapi.check_served <served spec URL> <pinned spec file name>

dev/e2e_native_test.sh runs it for MSS and the backend before the tests, so that a service
the SDK can no longer talk to fails the run that shows it. Only the schemas the SDK reads are
compared, and only as far as the SDK depends on them: a service of the same minor release may
add optional fields and schemas, and reword descriptions, as the SDK's models allow extra
fields; it may not drop or retype a field, require one the SDK does not send, or change an
enum's values.
"""
import json
import sys
import urllib.request
from typing import Any, Dict, List

from dev.openapi.generate import CONTRACTS, OPENAPI_DIR, make_lenient, prune_spec

# what documents a schema without changing what it accepts
DOCUMENTATION_KEYS = frozenset({"description", "title", "examples"})


def main(url: str, spec_name: str) -> int:
    """Prints how the served spec breaks the pinned one's schemas, if it does

    Returns:
        1 if any is incompatible, else 0
    """
    contract = next(c for c in CONTRACTS if c.spec_file.name == spec_name)
    with urllib.request.urlopen(url, timeout=30) as response:
        served = make_lenient(json.load(response)["components"]["schemas"])
    pinned = prune_spec(
        json.loads((OPENAPI_DIR / spec_name).read_text()), contract.schemas
    )["components"]["schemas"]

    problems = get_incompatibilities(pinned, served)
    if problems:
        print(
            f"{url} serves schemas the SDK's dev/openapi/{spec_name} cannot talk to:\n  "
            + "\n  ".join(problems)
        )
        return 1
    return 0


def get_incompatibilities(pinned: Dict[str, Any], served: Dict[str, Any]) -> List[str]:
    """Gets how the served schemas break the pinned ones, the SDK's

    Args:
        pinned: the SDK's schemas, by name
        served: the service's schemas, by name

    Returns:
        each incompatibility, as the schema path it is at and what changed
    """
    problems = []
    for name, schema in sorted(pinned.items()):
        if name not in served:
            problems.append(f"{name}: no longer served")
            continue
        _compare(schema, served[name], name, problems)
    return problems


def _compare(pinned: Any, served: Any, path: str, problems: List[str]) -> None:
    """Adds to the problems how the served node breaks the pinned one"""
    if not isinstance(pinned, dict) or not isinstance(served, dict):
        if pinned != served:
            problems.append(f"{path}: {pinned!r} became {served!r}")
        return

    pinned_properties = pinned.get("properties", {})
    served_properties = served.get("properties", {})
    for name, node in pinned_properties.items():
        if name not in served_properties:
            problems.append(f"{path}.{name}: no longer served")
        else:
            _compare(node, served_properties[name], f"{path}.{name}", problems)
    for name in set(served.get("required", [])) - set(pinned_properties):
        problems.append(f"{path}.{name}: required, but unknown to the SDK")

    for key in (pinned.keys() | served.keys()) - DOCUMENTATION_KEYS:
        if key in ("properties", "required"):
            continue
        if isinstance(pinned.get(key), dict):
            _compare(pinned[key], served.get(key), f"{path}[{key}]", problems)
        elif isinstance(pinned.get(key), list) and isinstance(served.get(key), list):
            _compare_list(pinned[key], served[key], f"{path}[{key}]", problems)
        elif pinned.get(key) != served.get(key):
            problems.append(
                f"{path}[{key}]: {pinned.get(key)!r} became {served.get(key)!r}"
            )


def _compare_list(
    pinned: List[Any], served: List[Any], path: str, problems: List[str]
) -> None:
    """Adds to the problems how the served list, e.g. an anyOf, breaks the pinned one"""
    if len(pinned) != len(served):
        problems.append(f"{path}: {len(pinned)} items became {len(served)}")
        return
    for index, (pinned_item, served_item) in enumerate(zip(pinned, served)):
        _compare(pinned_item, served_item, f"{path}[{index}]", problems)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
