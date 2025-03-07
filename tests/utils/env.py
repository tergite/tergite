# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2025
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""Test utilities for the environment"""
import os


def is_end_to_end() -> bool:
    """Checks if current environment is end to end

    Returns:
        True if the environment is in END_TO_END settings, False otherwise
    """
    return os.environ.get("IS_END_TO_END", "False").lower() == "true"


def is_in_docker() -> bool:
    """Checks if this is running in docker

    Returns:
        True if running in docker container settings, False otherwise
    """
    return os.environ.get("IS_IN_DOCKER", "False").lower() == "true"
