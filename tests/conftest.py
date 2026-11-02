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
import pytest

from tergite import Tergite
from tests.utils.env import is_end_to_end

if is_end_to_end():
    collect_ignore = ["integration"]
else:
    collect_ignore = ["e2e"]


@pytest.fixture(autouse=True)
def isolate_default_factory(monkeypatch, tmp_path):
    """Gives the default Tergite factory a temporary rc file and no providers, so that no
    test reads or writes the user's own ~/.qiskit/tergiterc"""
    monkeypatch.setattr(Tergite, "_rc_file", tmp_path / ".qiskit" / "tergiterc")
    monkeypatch.setattr(Tergite, "_providers", {})
    monkeypatch.setattr(Tergite, "_is_loaded", False)
