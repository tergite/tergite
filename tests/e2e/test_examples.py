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
"""End-to-end tests that the examples users start from run"""
import ast
import os
import subprocess
import sys
from pathlib import Path

HELLO_WORLD = Path(__file__).parents[2] / "examples" / "scripts" / "hello_world.py"


def test_hello_world_script(tmp_path):
    """examples/scripts/hello_world.py runs its circuit and prints the counts of its shots"""
    completed = subprocess.run(
        [sys.executable, str(HELLO_WORLD)],
        env={
            **os.environ,
            "HOME": str(tmp_path),
            "TERGITE_API_URL": os.environ["API_URL"],
            "TERGITE_API_TOKEN": os.environ["API_TOKEN"],
        },
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr
    counts = ast.literal_eval(completed.stdout.strip().splitlines()[-1])
    assert set(counts) <= {"0", "1"} and sum(counts.values()) == 1024
