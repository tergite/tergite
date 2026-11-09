# Running pulses

Pulses are written in [OpenPulse](https://openqasm.com/language/openpulse.html), part of
OpenQASM 3, by hand or with [oqpy](https://github.com/openqasm/oqpy). For oqpy and a backend's
frames as oqpy frames, install the `pulse` extra:

```shell
pip install 'tergite[pulse]'
```

## Who may send them

- Your project must be allowed pulse-level jobs, by an admin in the dashboard.
- The device must take them. Its operators set limits on amplitude, energy, frequency and
  duration; the backend checks each job against them and refuses it with the reason.

## The device's limits

`backend.pulse_limits` gives those limits, or `None` for a device that takes no pulse-level
jobs. The limits by kind of frame (`drive`, `readout`, `coupler`) leave out a kind that may
not be played at all.

```python
limits = backend.pulse_limits
print(limits.max_amplitude)   # {'drive': 0.5, 'readout': 0.3}
```

| Limit | Unit | What it bounds |
| --- | --- | --- |
| `max_amplitude` | fraction of full scale, by kind | the largest \|sample\| of a waveform |
| `max_frequency_offset` | Hz | how far `set_frequency`/`shift_frequency` move a frame from its calibrated frequency |
| `max_energy_per_shot` | full scale² · s, by kind | the sum of \|sample\|² · dt on one frame in one shot |
| `max_energy_per_job` | full scale² · s, by kind | the same over the job: per-shot energy × shots, summed over circuits |
| `max_pulse_duration` | s | a circuit's pulse-level blocks in one shot |
| `max_samples_per_waveform` | samples | one waveform, as played |
| `max_capture_duration` | s | one capture |

For a sense of the energies: a constant pulse of 0.3 for 100 ns is 0.3² × 100e-9 = 9e-9; at
1000 shots in each of two circuits, the job puts 1.8e-5 on that frame.

## Frames and the device's own gates

Pulses play on the frames the device publishes, such as `q00_drive`, `q00_readout` and
`q00_q01_coupler`.

- `backend.frames` gives those frames as oqpy frames, by name.
- `backend.calibrations` gives the `defcal`s of the device's gates, by gate and physical
  qubits. Each plays exactly what the gate does.

```python
import oqpy

frames = backend.frames
print(backend.calibrations[("x", (0,))])   # defcal x $0 { ... }
```

## Replacing a gate's pulses

`backend.run(circuits, calibrations=[...])` runs a job's gates with `defcal`s of your own, as
text or an oqpy program. For example, a gentler `x` on qubit 0:

```python
defcals = oqpy.Program()
gaussian = oqpy.declare_waveform_generator(
    "gaussian", [("amp", oqpy.complex128), ("d", oqpy.duration), ("sigma", oqpy.duration)]
)
with oqpy.defcal(defcals, oqpy.PhysicalQubits[0], "x"):
    defcals.play(frames["q00_drive"], gaussian(0.15, 40e-9, 10e-9))

job = backend.run(transpile(qc, backend), calibrations=[defcals])
```

## Running your own programs

`backend.run()` also takes programs, as OpenQASM 3 text or an oqpy program, beside circuits.
A program's `cal` blocks play, and `capture_v1` captures into classical bits. A job whose
program does not measure runs at `meas_level=1`, its captures as IQ points, unless you give
another level.

```python
program = oqpy.Program()
constant = oqpy.declare_waveform_generator(
    "constant", [("amp", oqpy.complex128), ("d", oqpy.duration)]
)
capture = oqpy.declare_extern("capture_v1", [("frame", oqpy.frame), ("d", oqpy.duration)], oqpy.bit)
c = oqpy.BitVar(name="c", size=1)
with oqpy.Cal(program):
    program.play(frames["q00_readout"], constant(0.1, 400e-9))
    program.set(c[0], capture(frames["q00_readout"], 400e-9))

job = backend.run(program, shots=1000)
job.wait_for_final_state()
print(job.result().get_memory())          # each shot's IQ point
```

[examples/scripts/pulse_level.py](../examples/scripts/pulse_level.py) runs a gate with a
`defcal` of its own and a `cal` block that captures.

## Migrating from pulse schedules

A `qiskit.pulse` schedule that ran on the previous SDK is rewritten in oqpy, each channel on
the frame of the same name in `backend.frames`:

| Channel | Frame |
| --- | --- |
| `DriveChannel(i)` | the drive of the `i`-th qubit by the number in its id, e.g. `q00_drive` |
| `MeasureChannel(i)`, `AcquireChannel(i)` | that qubit's readout, e.g. `q00_readout` |
| `ControlChannel(k)` | the coupler the device names `u{k}`, e.g. `q00_q01_coupler` |

```python
# before, with Qiskit 1.x
with pulse.build() as schedule:
    pulse.play(pulse.Drag(40, 0.2, 10, 2.0), pulse.DriveChannel(0))
    pulse.shift_phase(0.5, pulse.DriveChannel(0))
    pulse.acquire(1000, pulse.AcquireChannel(0), pulse.MemorySlot(0))
job = backend.run(schedule)

# now
frames = backend.frames
drag = oqpy.declare_waveform_generator(
    "drag",
    [("amp", oqpy.complex128), ("d", oqpy.duration), ("sigma", oqpy.duration), ("beta", oqpy.float64)],
)
c = oqpy.BitVar(name="c", size=1)
program = oqpy.Program()
with oqpy.Cal(program):
    program.play(frames["q00_drive"], drag(0.2, 40e-9, 10e-9, 2e-9))
    program.shift_phase(frames["q00_drive"], 0.5)
program.measure(oqpy.PhysicalQubits[0], c[0])
job = backend.run(program)
```

What changes:

- **Durations are in seconds**, not samples. A sample is 1 ns. A Drag's `beta`, which qiskit
  counts in samples, is in seconds too.
- **Waveforms** are OpenPulse's `constant`, `gaussian`, `gaussian_square`, `drag`, `sech` and
  `sine`, or arrays of samples (`oqpy.WaveformVar(samples)`). An array reproduces any qiskit
  pulse exactly from its `get_waveform().samples`. Note that qiskit lifts its Gaussians so
  their ends are zero; OpenPulse's are not lifted.
- **An acquisition** becomes `measure`, with the device's calibrated readout, as above. For raw
  IQ points, use a `capture_v1` in the `cal` block instead; it runs after a readout pulse on
  the same frame, not alongside it.
- **A phase or frequency change** takes 4 ns of its frame, where qiskit counts none.
