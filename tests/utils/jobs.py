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
"""Test utilities for jobs running on the real stack"""
from tergite import Job

# Qiskit's default polls every 5 seconds, longer than a simulator job takes
JOB_POLL_SECONDS = 0.2
JOB_TIMEOUT_SECONDS = 120


def wait_for_final_state(job: Job) -> None:
    """Waits until the job is done, failed or cancelled, polling often

    Args:
        job: the job to wait for

    Raises:
        JobTimeoutError: the job did not end within JOB_TIMEOUT_SECONDS
    """
    job.wait_for_final_state(timeout=JOB_TIMEOUT_SECONDS, wait=JOB_POLL_SECONDS)
