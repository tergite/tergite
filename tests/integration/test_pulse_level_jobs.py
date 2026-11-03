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
"""Tests of pulse-level jobs: running OpenQASM 3 programs, running gates with defcals, and
the device's frames and defcals"""
import oqpy
import pytest
from qiskit import QuantumCircuit, transpile

from tergite import Tergite, TergiteBackend
from tests.utils.uploads import get_uploaded_job_file

from .conftest import API_URL, TEST_CALIBRATIONS_MAP

CAPTURE_PROGRAM = """OPENQASM 3.0;
defcalgrammar "openpulse";
bit[2] c;
cal {
    play(q00_readout, constant(0.1, 400ns));
    c[1] = capture_v1(q00_readout, 400ns);
}
"""
MEASURE_PROGRAM = """OPENQASM 3.0;
defcalgrammar "openpulse";
bit c;
cal {
    play(q00_drive, gaussian(0.2, 40ns, 10ns));
}
c = measure $0;
"""
X_DEFCAL = """defcal x $0 {
    play(q00_drive, gaussian(0.2, 40ns, 10ns));
}"""
FRAMES = [
    {"name": "q00_drive", "kind": "drive", "qubits": [0], "frequency": 4.6e9},
    {"name": "q00_readout", "kind": "readout", "qubits": [0], "frequency": 6.8e9},
]
DEFCALS = [{"gate": "x", "qubits": [0], "program": X_DEFCAL}]


def test_run_uploads_a_program_as_it_is(api):
    backend = _get_backend()

    job = backend.run(CAPTURE_PROGRAM, shots=10)

    [circuit] = get_uploaded_job_file(api).params.circuits
    assert (circuit.name, circuit.qasm, circuit.num_clbits) == (
        "program_0",
        CAPTURE_PROGRAM,
        2,
    )
    assert job.job_id()


@pytest.mark.parametrize(
    "program, options, expected",
    [
        (CAPTURE_PROGRAM, {}, 1),
        (MEASURE_PROGRAM, {}, 2),
        (CAPTURE_PROGRAM, {"meas_level": 2}, 2),
    ],
    ids=["captures", "measures", "given"],
)
def test_run_of_a_program_that_does_not_measure_is_at_meas_level_1(
    api, program, options, expected
):
    backend = _get_backend()

    backend.run(program, **options)

    assert get_uploaded_job_file(api).params.meas_level == expected


def test_run_uploads_an_oqpy_program_with_its_externs_in_a_cal_block(api):
    backend = _get_backend()
    program = oqpy.Program()
    gaussian = oqpy.declare_waveform_generator(
        "gaussian",
        [("amp", oqpy.complex128), ("d", oqpy.duration), ("sigma", oqpy.duration)],
    )
    drive = _get_frame("q00_drive", 4.6e9)
    with oqpy.Cal(program):
        program.play(drive, gaussian(0.2, 40e-9, 10e-9))

    backend.run(program)

    [circuit] = get_uploaded_job_file(api).params.circuits
    assert circuit.qasm.startswith('OPENQASM 3.0;\ndefcalgrammar "openpulse";\ncal {\n')
    assert "extern gaussian" in circuit.qasm.split("}")[0]
    # the device defines its frames, so the program declares none
    assert "frame " not in circuit.qasm and "port " not in circuit.qasm


def test_run_adds_the_calibrations_to_each_circuit_and_program(api):
    backend = _get_backend()
    circuit = _get_x_circuit(backend)
    defcal_program = oqpy.Program()
    with oqpy.defcal(defcal_program, oqpy.PhysicalQubits[1], "x"):
        defcal_program.delay(40e-9, _get_frame("q01_drive", 4.7e9))

    backend.run([circuit, MEASURE_PROGRAM], calibrations=[X_DEFCAL, defcal_program])

    first, second = [c.qasm for c in get_uploaded_job_file(api).params.circuits]
    assert first.startswith(
        f'OPENQASM 3.0;\ninclude "stdgates.inc";\ndefcalgrammar "openpulse";\n{X_DEFCAL}\n'
    )
    assert "defcal x $1 {\n    delay[40.0ns] q01_drive;\n}" in first
    assert first.index("defcal x $1") < first.index("bit[1] c;")
    # the program has its grammar already, so it is not declared twice
    assert second.count("defcalgrammar") == 1
    assert second.index(X_DEFCAL) < second.index("bit c;")


def test_frames_and_calibrations_are_those_of_the_latest_calibration(api, monkeypatch):
    _publish_pulse_calibration(monkeypatch)
    backend = _get_backend()

    frames = backend.frames
    calibrations = backend.calibrations

    assert set(frames) == {"q00_drive", "q00_readout"}
    drive = frames["q00_drive"]
    assert isinstance(drive, oqpy.FrameVar)
    assert drive.name == "q00_drive"
    assert drive.init_expression.args["frequency"] == 4.6e9
    assert calibrations == {("x", (0,)): X_DEFCAL}


def test_a_published_frame_is_played_without_a_declaration(api, monkeypatch):
    _publish_pulse_calibration(monkeypatch)
    backend = _get_backend()
    program = oqpy.Program()
    constant = oqpy.declare_waveform_generator(
        "constant", [("amp", oqpy.complex128), ("d", oqpy.duration)]
    )
    with oqpy.Cal(program):
        program.play(backend.frames["q00_drive"], constant(0.1, 40e-9))

    backend.run(program)

    [circuit] = get_uploaded_job_file(api).params.circuits
    assert "play(q00_drive, constant(0.1, 40.0ns));" in circuit.qasm
    assert "newframe" not in circuit.qasm


def test_a_device_that_takes_no_pulse_level_jobs_has_no_frames_or_calibrations(api):
    backend = _get_backend()

    assert (backend.frames, backend.calibrations) == ({}, {})


def _get_backend() -> TergiteBackend:
    """Gets Loke's backend through a new test provider"""
    provider = Tergite.use_provider_account(service_name="test", url=API_URL)
    return provider.get_backend("loke")


def _get_x_circuit(backend: TergiteBackend) -> QuantumCircuit:
    """Gets an X on qubit 0, measured, transpiled to the backend"""
    circuit = QuantumCircuit(1, 1)
    circuit.x(0)
    circuit.measure(0, 0)
    return transpile(circuit, backend=backend, initial_layout=[0])


def _get_frame(name: str, frequency: float) -> oqpy.FrameVar:
    """Gets a frame the device defines, which a program plays on without declaring it"""
    port = oqpy.PortVar(f"{name}_port", needs_declaration=False)
    return oqpy.FrameVar(port, frequency, 0.0, name=name, needs_declaration=False)


def _publish_pulse_calibration(monkeypatch) -> None:
    """Makes Loke's calibration, as MSS serves it, carry frames and defcals"""
    calibration = {
        **TEST_CALIBRATIONS_MAP["loke"],
        "frames": FRAMES,
        "defcals": DEFCALS,
    }
    monkeypatch.setitem(TEST_CALIBRATIONS_MAP, "loke", calibration)
