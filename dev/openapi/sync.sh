#!/bin/bash
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
#
# Copies the OpenAPI specs this SDK speaks to from the services' checkouts, at the versions
# the SDK targets, and regenerates the SDK's models from them.
#
# Usage
# =====
#
#   FRONTEND_PATH=../tergite-frontend ./dev/openapi/sync.sh

set -e # exit if any step fails

ROOT_PATH="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND_PATH="${FRONTEND_PATH:-$ROOT_PATH/../tergite-frontend}"

cp "$FRONTEND_PATH/dev/openapi/openapi.json" "$ROOT_PATH/dev/openapi/mss.json"
cd "$ROOT_PATH" && uv run --frozen python -m dev.openapi.generate
