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
"""Tests of the transpiler target of a device"""
import pytest

from tergite.api.mss_models import Device, DeviceCalibration
from tergite.target import get_target
from tests.utils.fixtures import load_json_fixture

DEVICES = {d["name"]: d for d in load_json_fixture("many_backends.json")}
CALIBRATIONS = {c["name"]: c for c in load_json_fixture("calibrations.json")}
CZ_SECONDS = 88e-9 + 25e-9 + 370e-9 + 88e-9


@pytest.mark.parametrize("name", ["loke", "qiskit_pulse_1q", "qiskit_pulse_2q"])
def test_every_qubit_has_the_single_qubit_gates(name: str):
    """rz, sx, x, rx, measure, reset and delay are on every qubit"""
    target = _get_target(name)
    qubits = {(q,) for q in range(DEVICES[name]["number_of_qubits"])}

    for gate in ("rz", "sx", "x", "rx", "measure", "reset", "delay"):
        assert set(target.qargs_for_operation_name(gate)) == qubits


def test_cz_on_each_calibrated_pair():
    """cz is on both directions of the coupled pair whose coupler is calibrated"""
    target = _get_target("qiskit_pulse_2q")

    assert set(target.qargs_for_operation_name("cz")) == {(0, 1), (1, 0)}
    assert target["cz"][(0, 1)].duration == pytest.approx(CZ_SECONDS)


def test_no_cz_without_couplers():
    """A device without calibrated couplers has no cz"""
    calibration = {**CALIBRATIONS["qiskit_pulse_2q"], "couplers": []}

    target = get_target(
        Device.model_validate(DEVICES["qiskit_pulse_2q"]),
        DeviceCalibration.model_validate(calibration),
    )

    assert "cz" not in target.operation_names


def test_durations_and_qubit_properties_come_from_the_calibration():
    """Gates last as calibrated, rz takes no time, and qubits carry T1 and frequency"""
    target = _get_target("loke")
    qubit = CALIBRATIONS["loke"]["qubits"][0]

    assert target["x"][(0,)].duration == qubit["pi_pulse_duration"]["value"]
    assert target["rz"][(0,)].duration == 0.0
    assert target["measure"][(0,)].duration == 9e-07
    assert target.qubit_properties[0].t1 == qubit["t1_decoherence"]["value"]
    assert target.qubit_properties[0].frequency == qubit["frequency"]["value"]


def test_device_without_calibration():
    """A device not characterized gets the gates without durations"""
    target = get_target(Device.model_validate(DEVICES["qiskit_pulse_2q"]), None)

    assert target["x"][(0,)].duration is None
    assert "cz" not in target.operation_names


def _get_target(name: str):
    return get_target(
        Device.model_validate(DEVICES[name]),
        DeviceCalibration.model_validate(CALIBRATIONS[name]),
    )
