# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from qiskit.providers import BaseBackend
from qiskit.providers.models import BackendConfiguration, BackendProperties
from qiskit.result import Result
from .job import Job
import pathlib
import json
import requests
from uuid import uuid4
from .hardcoded_backend_data import properties as pingu_prop_dict


class Backend(BaseBackend):
    def __init__(self, configuration: BackendConfiguration, provider):
        super().__init__(configuration=configuration, provider=provider)
        self._properties = None
        print("Tergite: Class Backend initialized")

    def run(self, qobj):
        MSS_URL = "http://qdp-git.mc2.chalmers.se:5000/jobs"
        job_registration = requests.post(MSS_URL).json()
        job_id = job_registration["job_id"]
        job_upload_url = job_registration["upload_url"]

        job_entry = {
            "job_id": job_id,
            "type": "script",
            "name": "qiskit_qasm_runner",
            "params": {"qobj": qobj.to_dict()},
        }

        job_file = pathlib.Path("/tmp") / str(uuid4())
        with job_file.open("w") as dest:
            json.dump(job_entry, dest)

        with job_file.open("r") as src:
            files = {"upload_file": src}
            response = requests.post(job_upload_url, files=files)

            if response:
                print("Tergite: Job has been successfully submitted")

        job_file.unlink()

        backend_name = self.name()
        job = Job(backend_name, job_id, qobj)
        return job

    def properties(self):
        if self._properties is None:
            self._properties = BackendProperties.from_dict(pingu_prop_dict)

        return self._properties
