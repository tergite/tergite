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
"""Tests for what a service of the same minor release may change in the schemas the SDK uses"""
import copy

import pytest

from dev.openapi.check_served import get_incompatibilities

PINNED = {
    "Job": {
        "title": "Job",
        "description": "A job",
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "title": "Job Id"},
            "status": {"$ref": "#/components/schemas/JobStatus"},
        },
        "required": ["job_id"],
    },
    "JobStatus": {"type": "string", "enum": ["pending", "successful"]},
}


def test_added_optional_fields_and_reworded_docs_are_compatible():
    served = copy.deepcopy(PINNED)
    served["Job"]["description"] = "A job, as MSS keeps it"
    served["Job"]["properties"]["duration"] = {"type": "number"}
    served["Device"] = {"type": "object"}

    assert get_incompatibilities(PINNED, served) == []


@pytest.mark.parametrize(
    "change, expected",
    [
        (
            lambda s: s["Job"]["properties"].pop("job_id"),
            "Job.job_id: no longer served",
        ),
        (
            lambda s: s["Job"]["properties"]["job_id"].update(type="integer"),
            "Job.job_id[type]: 'string' became 'integer'",
        ),
        (
            lambda s: s["Job"].update(required=["job_id", "device"]),
            "Job.device: required, but unknown to the SDK",
        ),
        (lambda s: s["JobStatus"]["enum"].append("failed"), "JobStatus[enum]"),
        (lambda s: s.pop("JobStatus"), "JobStatus: no longer served"),
    ],
)
def test_what_the_sdk_depends_on_may_not_change(change, expected):
    served = copy.deepcopy(PINNED)
    change(served)

    problems = get_incompatibilities(PINNED, served)

    assert any(problem.startswith(expected) for problem in problems), problems
