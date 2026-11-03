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
# Records the performance measures into <out-dir>: the client benchmarks against a mocked MSS
# and backend into client.json, then the round trip of jobs against the native e2e stack into
# roundtrip.json, which dev/e2e_native_test.sh starts with the same FRONTEND_* and BACKEND_*
# variables. A second argument records one alone: client or roundtrip.
#
# Usage
# =====
#
#   FRONTEND_PATH=../tergite-frontend BACKEND_PATH=../tergite-backend \
#     ./dev/perf/record.sh dev/perf/baselines    # the baseline
#   ./dev/perf/record.sh /tmp/perf client        # the client alone, to compare with it
#   uv run python dev/perf/compare.py dev/perf/baselines /tmp/perf
#
# Compare only runs made on the same machine: the numbers are this machine's.

set -e # exit if any step fails

ROOT_PATH="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_PATH="$(mkdir -p "$1" && cd "$1" && pwd)"
ONLY="$2"

cd "$ROOT_PATH"
if [[ -z "$ONLY" || "$ONLY" = "client" ]]; then
  echo "Recording the client benchmarks"
  # at least 20 rounds, as one slow round moved the median of run's 10 past the noise floor
  uv run --frozen pytest -q -p no:cacheprovider dev/perf/test_client.py \
    --benchmark-min-rounds=20 --benchmark-json="$OUT_PATH/client.json"
fi
if [[ -z "$ONLY" || "$ONLY" = "roundtrip" ]]; then
  echo "Recording the round trip"
  PYTEST_TARGET=dev/perf/test_roundtrip.py PERF_DIR="$OUT_PATH" ./dev/e2e_native_test.sh -q
fi
