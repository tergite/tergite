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
"""Checks that a running service serves the schemas the SDK's pinned copy of its spec has

Usage: python -m dev.openapi.check_served <served spec URL> <pinned spec file name>

dev/e2e_native_test.sh runs it for MSS and the backend before the tests, so that a drift
between the pinned copy and the real service fails the run that shows it. Only the schemas
the SDK reads are compared: the rest, such as MSS's /auth/{provider} routes, which follow
its config, are none of the SDK's business.
"""
import json
import sys
import urllib.request

from dev.openapi.generate import CONTRACTS, OPENAPI_DIR, prune_spec


def main(url: str, spec_name: str) -> int:
    """Prints the schemas that differ between the served and the pinned spec

    Returns:
        1 if any differs, else 0
    """
    contract = next(c for c in CONTRACTS if c.spec_file.name == spec_name)
    with urllib.request.urlopen(url, timeout=30) as response:
        served = prune_spec(json.load(response), contract.schemas)
    pinned = prune_spec(
        json.loads((OPENAPI_DIR / spec_name).read_text()), contract.schemas
    )

    served_schemas = served["components"]["schemas"]
    pinned_schemas = pinned["components"]["schemas"]
    differing = sorted(
        name
        for name in served_schemas.keys() | pinned_schemas.keys()
        if served_schemas.get(name) != pinned_schemas.get(name)
    )
    if differing:
        print(
            f"{url} serves schemas that differ from dev/openapi/{spec_name}: "
            f"{', '.join(differing)}; run dev/openapi/sync.sh against its checkout"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
