# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
from qiskit.providers import BackendV2
from qiskit.providers.models import BackendConfiguration
from qiskit.providers import Options
from qiskit.pulse.channels import (
    DriveChannel,
    MeasureChannel,
    AcquireChannel,
    ControlChannel,
)
from qiskit.pulse.channels import MemorySlot
from qiskit.qobj import PulseQobj

import qiskit.compiler as compiler

# typing
from qiskit.transpiler import Target
from qiskit.pulse import Schedule, ScheduleBlock
from qiskit.transpiler.coupling import CouplingMap
from numpy import inf as infinity
from abc import abstractmethod
from typing import (
    #   Optional,
    List,
    Union,
    Iterable,
    #   Tuple
)

# job transmission and result retrieval
# from qiskit.result import Result
import pathlib
import json
import requests
from tempfile import gettempdir
from uuid import uuid4
from .job import Job
from .json_encoder import IQXJsonEncoder
from .config import REST_API_MAP
from .serialization import iqx_rle


class Backend(BackendV2):
    def __init__(self, /, provider: object, base_url: str, **kwargs):
        super().__init__(provider=provider, **kwargs)
        self._base_url = base_url

    @property
    def base_url(self) -> str:
        return self._base_url

    @abstractmethod
    def target(self) -> Target:
        """
        Please see: https://qiskit.org/documentation/_modules/qiskit/transpiler/target.html#Target
        """
        ...

    def configuration(self) -> BackendConfiguration:
        """
        Remark: Qiskit code calls this method as a function, which is why
                this method is not decorated as a @property.

        This method mainly exists for backward compatibility with functions that
        use the old Backend inheritance pattern (it will be phased out).

        The configuration is where you’ll find data about the static setup of the device,
        such as its name, version, the number of qubits, and the types of features it supports.
        """
        return BackendConfiguration(
            backend_name=self.name,  # from super
            backend_version=self.backend_version,  # from super
            n_qubits=self.num_qubits,  # from self.target
            basis_gates=NotImplemented,
            gates=NotImplemented,
            simulator=False,  # this is a real quantum computer
            conditional=False,  # we cannot do conditional gate application (yet)
            local=False,  # jobs are sent over the internet
            open_pulse=True,
            meas_levels=(0, 1, 2),  # 0: RAW, 1: KERNELED, 2: DISCRIMINATED
            memory=False,  # ?
            max_shots=infinity,  # should be the same as validator of set_options(shots = ...)
            coupling_map=self.coupling_map,  # by inheriting class
            supported_instructions=self.instructions,  # from self.target
            dt=self.dt,  # from self.target
            dtm=self.dtm,  # from self.dtm
            description=self.description,  # from superior
        )

    @property
    def max_circuits(self):
        """
        Maximum number of circuits that can be sent in a single QOBJ.
        Should probably have an upper bound here.
        """
        return infinity

    @classmethod
    def _default_options(cls, /) -> Options:
        """
        This defines the default user configurable settings of this backend.
        The user can set anything set in _default_options with BackendV2.set_options.
        """
        options = Options(shots=2000)
        options.set_validator(
            "shots", (1, infinity)
        )  # probably want an upper limit on this one
        return options

    @property
    def dtm(self) -> float:
        """
        The sampling rate of the control rack’s analog-to-digital converters (ADCs)
        is also relevant for measurement level 0; dtm is the time per sample returned
        """
        return self.dt  # for QBLOX it's the same as dt

    @abstractmethod
    def meas_map(self) -> List[List[int]]:
        """
        Indicates which qubits are connected to the same readout lines.
        All qubits in k-simplex (k > 0) in map are connected to the same readout line.
        e.g.
           If the map is [[0],[1,2]], we have that qubit 1 and qubit 2 are connected to the same readout line.
           and if the map is [[i for i in range( self.num_qubits )]], we have that all qubits are connected
           to the same readout line.
        """
        ...

    @abstractmethod
    def qubit_lo_freq(self) -> List[float]:
        """
        The estimated frequencies of the qubits. Units should be Hz.
        e.g.
            If qubit 0 is @ 4 GHz and qubit 1 is @ 4.1 GHz, then
            this should return [4e9, 4.1e9].
        """
        ...

    @abstractmethod
    def meas_lo_freq(self) -> List[float]:
        """
        The estimated frequencies of the readout resonators. Units should be Hz.
        e.g.
            If resonator for qubit 0 is @ 6 GHz and the resonator for qubit 1 is @ 6.1 GHz, then
            this should return [6e9, 6.1e9].
        """
        ...

    @abstractmethod
    def coupling_map(self) -> CouplingMap:
        """
        This coupling map specifies 'which qubit is which'. This is a directed graph
        where a -> b if a is coupled to b.

        The coupling map can either be hardcoded or generated from the two-qubit gate
        definitions of self.Target, although the latter makes less sense since
        the coupling map exists before the gate definitions.
        """
        ...

    def drive_channel(self, qubit: int, /):
        return DriveChannel(qubit)

    def measure_channel(self, qubit: int, /):
        return MeasureChannel(qubit)

    def acquire_channel(self, qubit: int, /):
        return AcquireChannel(qubit)

    def memory_slot(self, qubit: int, /):
        return MemorySlot(qubit)

    def control_channel(self, qubits: Iterable[int], /):
        """
        You can only influence the control between qubit i and qubit j if
        (i,j) is in the coupling map, i.e. if they are physically coupled.
        """
        qubits = tuple(qubits)

        if len(qubits) != 2:
            raise NotImplementedError("Only pairwise coupling supported.")

        i, j = qubits
        assert (
            qubits in self.coupling_map.get_edges()
        ), f"Directed coupling {i}->{j} not in coupling map."
        return [ControlChannel(q) for q in qubits]

    def run(self, circuits: Union[object, List[object]], /, **kwargs) -> Job:
        # --------- Register job
        JOBS_URL = self.base_url + REST_API_MAP["jobs"]
        job_registration = requests.post(JOBS_URL).json()
        job_id = job_registration["job_id"]
        job_upload_url = job_registration["upload_url"]

        # --------- Convert any circuits to pulse schedules
        if not isinstance(circuits, list):
            circuits = [circuits]

        schedules = list()
        for circ in circuits:
            if isinstance(circ, Schedule) or isinstance(circ, ScheduleBlock):
                schedules.append(circ)
            else:
                schedules.append(
                    compiler.schedule(
                        compiler.transpile(circ, backend=self), backend=self
                    )
                )

        # --------- Try to make a nice human readable tag (for all experiments)
        qobj_header = (
            dict() if "qobj_header" not in kwargs else kwargs.pop("qobj_header")
        )
        if "tag" not in qobj_header:
            qobj_header["tag"] = (
                circuits[0].name if type(circuits) == list else circuits.name
            )
            if type(circuits) == list:
                for circ in circuits:
                    if circ.name != qobj_header["tag"]:
                        qobj_header["tag"] = ""
                        break
            qobj_header["tag"] = qobj_header["tag"].replace(" ", "_")

        qobj_header["dt"] = self.dt  # for some reason this is not in the config
        qobj_header["dtm"] = self.dtm  # for some reason this is not in the config

        # --------- Assemble the PulseQobj
        qobj = compiler.assemble(
            experiments=schedules,
            backend=self,
            shots=self.options.shots,
            meas_map=self.meas_map,
            qubit_lo_range=[[0, 10e9]] * self.num_qubits,
            meas_lo_range=[[0, 10e9]] * self.num_qubits,
            meas_level=1 if "meas_level" not in kwargs else kwargs.pop("meas_level"),
            meas_return="avg"
            if "meas_return" not in kwargs
            else kwargs.pop("meas_return"),
            qubit_lo_freq=self.qubit_lo_freq,  # qubit frequencies (base + if)
            meas_lo_freq=self.meas_lo_freq,  # resonator frequencies (base + if)
            qobj_header=qobj_header,
            parametric_pulses=[
                "constant",
                "zero",
                "square",
                "sawtooth",
                "triangle",
                "cos",
                "sin",
                "gaussian",
                "gaussian_deriv",
                "sech",
                "sech_deriv",
                "gaussian_square",
                "drag",
            ],
            **kwargs,
        )

        qobj = PulseQobj.to_dict(qobj)

        # --------- RLE pulse library (for compression)
        for pulse in qobj["config"]["pulse_library"]:
            pulse["samples"] = iqx_rle(pulse["samples"])

        # --------- Transmit job
        job_entry = {
            "job_id": job_id,
            "type": "script",
            "name": "pulse_schedule",
            "params": {"qobj": qobj},
        }

        # create a temporary file for transmission
        # job_file = pathlib.Path("/tmp") / str(uuid4())
        job_file = pathlib.Path(gettempdir()) / str(uuid4())
        with job_file.open("w") as dest:
            json.dump(job_entry, dest, cls=IQXJsonEncoder, indent="\t")

        with job_file.open("r") as src:
            files = {"upload_file": src}
            response = requests.post(job_upload_url, files=files)

            if response:
                print("Tergite: Job has been successfully submitted")

        # delete temporary transmission file
        job_file.unlink()

        job = Job(backend=self, job_id=job_id, qobj=qobj)
        return job
