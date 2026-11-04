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
"""Pulse-level jobs: OpenQASM 3 programs with OpenPulse, the defcals a job's gates run
with, and a device's frames as oqpy frames"""
import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from ..exc import TergiteError

if TYPE_CHECKING:
    import oqpy

    from ..clients.mss.models import DeviceCalibration

OPENPULSE_GRAMMAR = 'defcalgrammar "openpulse";'
# what a program opens with, before which no defcal it is given may go
HEADER_PREFIXES = ("OPENQASM", "include", "defcalgrammar")
PULSE_EXTRA_HINT = "install the pulse extra: pip install 'tergite[pulse]'"
# how to write a qiskit.pulse schedule again in OpenPulse
MIGRATION_GUIDE_URL = (
    "https://github.com/tergite/tergite#migrating-from-pulse-schedules"
)


@dataclass(frozen=True)
class ProgramInfo:
    """What the SDK reads of a pulse-level program: its classical registers and whether it
    measures"""

    creg_sizes: List[List[Any]]
    is_measuring: bool

    @property
    def num_clbits(self) -> int:
        """The number of the program's classical bits"""
        return sum(size for _, size in self.creg_sizes)


def get_program_qasm(program: Any) -> str:
    """Gets the OpenQASM 3 of a pulse-level program: text as it is, or what its to_qasm()
    writes; an oqpy Program's with its extern declarations in a cal block, as the backend
    reads them

    Args:
        program: OpenQASM 3 text, or anything with to_qasm(), e.g. an oqpy Program

    Returns:
        the program's OpenQASM 3

    Raises:
        TergiteError: Tergite backends run circuits or OpenQASM 3 programs, not {type}
    """
    if isinstance(program, str):
        return program
    to_qasm = getattr(program, "to_qasm", None)
    if not callable(to_qasm):
        raise TergiteError(
            "Tergite backends run circuits or OpenQASM 3 programs, not "
            f"{type(program).__name__}; a pulse schedule is written in OpenPulse now: "
            f"{MIGRATION_GUIDE_URL}"
        )
    if _is_oqpy_program(program):
        return to_qasm(encal_declarations=True)
    return to_qasm()


def get_program_info(qasm: str) -> ProgramInfo:
    """Gets the classical registers of a pulse-level program, and whether it measures

    Args:
        qasm: the program's OpenQASM 3

    Returns:
        each register's name and size, in the order declared, and whether it measures

    Raises:
        TergiteError: install the pulse extra: pip install 'tergite[pulse]'
        TergiteError: the program is not OpenQASM 3: {reason}
    """
    parse = _load_openpulse_parse()
    try:
        program = parse(qasm)
    except Exception as exp:
        raise TergiteError(f"the program is not OpenQASM 3: {exp}") from exp
    return ProgramInfo(
        creg_sizes=_get_creg_sizes(program.statements),
        is_measuring=any(_is_measuring(v) for v in program.statements),
    )


def get_calibration_qasm(calibration: Any) -> str:
    """Gets the OpenQASM 3 of a calibration a job's gates run with: defcal text as it is, or
    what an oqpy Program of defcals, or anything with to_qasm(), writes, less the header
    a program it goes into has already

    Args:
        calibration: defcal text, or anything with to_qasm(), e.g. an oqpy Program

    Returns:
        the calibration's statements

    Raises:
        TergiteError: a calibration is defcal text or has to_qasm(), not {type}
    """
    if isinstance(calibration, str):
        return calibration.strip()
    if not callable(getattr(calibration, "to_qasm", None)):
        raise TergiteError(
            "a calibration is defcal text or has to_qasm(), not "
            f"{type(calibration).__name__}"
        )
    lines = get_program_qasm(calibration).splitlines()
    return "\n".join(
        line for line in lines if not line.strip().startswith(HEADER_PREFIXES)
    ).strip()


def add_calibrations(qasm: str, calibrations: Sequence[str]) -> str:
    """Adds the calibrations to a program, after its header, with the OpenPulse grammar
    they are written in where it lacks it, so that its gates run with them

    Args:
        qasm: the program's OpenQASM 3
        calibrations: the calibrations' statements, e.g. defcals

    Returns:
        the program, with them; as it is for none
    """
    if not calibrations:
        return qasm
    lines = qasm.splitlines()
    header_end = _get_header_end(lines)
    has_grammar = any(
        line.strip().startswith("defcalgrammar") for line in lines[:header_end]
    )
    added = [] if has_grammar else [OPENPULSE_GRAMMAR]
    added.extend(calibrations)
    return "\n".join([*lines[:header_end], *added, *lines[header_end:]]) + "\n"


def get_frames(
    calibration: Optional["DeviceCalibration"],
) -> Dict[str, "oqpy.FrameVar"]:
    """Gets the frames a device's pulse-level jobs may play on, as oqpy frames that a
    program names without declaring, as the device defines them

    Args:
        calibration: the device's latest calibration, or None if it is not characterized

    Returns:
        the frames, by name, e.g. q12_drive, at their calibrated frequencies; none for a
        device that takes no pulse-level jobs

    Raises:
        TergiteError: install the pulse extra: pip install 'tergite[pulse]'
    """
    oqpy = _load_oqpy()
    frames = (calibration.frames if calibration else None) or []
    return {
        frame.name: oqpy.FrameVar(
            oqpy.PortVar(f"{frame.name}_port", needs_declaration=False),
            frame.frequency,
            0.0,
            name=frame.name,
            needs_declaration=False,
        )
        for frame in frames
    }


def get_calibrations(
    calibration: Optional["DeviceCalibration"],
) -> Dict[Tuple[str, Tuple[int, ...]], str]:
    """Gets the defcals of a device's gates, which a job may run its gates with as they are,
    or change

    Args:
        calibration: the device's latest calibration, or None if it is not characterized

    Returns:
        each defcal's OpenQASM 3, by its gate and physical qubits, e.g. ("x", (0,)); none
        for a device that takes no pulse-level jobs
    """
    defcals = (calibration.defcals if calibration else None) or []
    return {(defcal.gate, tuple(defcal.qubits)): defcal.program for defcal in defcals}


def _is_oqpy_program(program: Any) -> bool:
    """Whether the program is an oqpy Program, without importing oqpy where it is not"""
    return type(program).__module__.split(".")[0] == "oqpy"


def _load_openpulse_parse() -> Any:
    """Loads openpulse's parser, which the pulse extra installs

    Raises:
        TergiteError: install the pulse extra: pip install 'tergite[pulse]'
    """
    try:
        from openpulse import parse
    except ImportError as exp:
        raise TergiteError(
            f"reading a pulse-level program: {PULSE_EXTRA_HINT}"
        ) from exp
    return parse


def _load_oqpy() -> Any:
    """Loads oqpy, which the pulse extra installs

    Raises:
        TergiteError: install the pulse extra: pip install 'tergite[pulse]'
    """
    try:
        import oqpy
    except ImportError as exp:
        raise TergiteError(f"the backend's frames: {PULSE_EXTRA_HINT}") from exp
    return oqpy


def _get_creg_sizes(statements: Sequence[Any]) -> List[List[Any]]:
    """Gets the name and size of each classical bit register the statements declare"""
    from openpulse import ast

    creg_sizes = []
    for statement in statements:
        if isinstance(statement, ast.ClassicalDeclaration) and isinstance(
            statement.type, ast.BitType
        ):
            size = statement.type.size
            creg_sizes.append([statement.identifier.name, size.value if size else 1])
    return creg_sizes


def _is_measuring(node: Any) -> bool:
    """Whether the node, or one within it, measures a qubit; a pulse-level block does not,
    its captures being read as IQ points"""
    from openpulse import ast

    if isinstance(node, ast.QuantumMeasurement):
        return True
    if isinstance(node, (ast.CalibrationStatement, ast.CalibrationDefinition)):
        return False
    if isinstance(node, list):
        return any(_is_measuring(item) for item in node)
    if dataclasses.is_dataclass(node):
        return any(
            _is_measuring(getattr(node, field.name))
            for field in dataclasses.fields(node)
        )
    return False


def _get_header_end(lines: List[str]) -> int:
    """Gets the index of the first line after the program's header: its version, includes
    and grammar, and the blank lines among them"""
    header_end = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith(HEADER_PREFIXES):
            break
        header_end = index + 1
    return header_end
