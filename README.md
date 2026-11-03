# Tergite

[![PyPI version](https://badge.fury.io/py/tergite.svg)](https://pypi.python.org/pypi/tergite/) [![license](https://img.shields.io/pypi/l/tergite.svg)](https://pypi.python.org/pypi/tergite/) [![CI](https://github.com/tergite/tergite/actions/workflows/ci.yml/badge.svg)](https://github.com/tergite/tergite/actions) [![PyPI pyversions](https://img.shields.io/pypi/pyversions/tergite.svg)](https://pypi.python.org/pypi/tergite/)  

The SDK in the [Tergite software stack](https://tergite.github.io/) for connecting to the Swedish quantum computer.    

It includes:

- [Qiskit](https://github.com/Qiskit/qiskit) providers

**This project is developed by a core group of collaborators.**
**Chalmers Next Labs AB (CNL) takes on the role of managing and maintaining this project.**

## Version Control

The tergite stack is developed on a separate version control system and mirrored on Github.
If you are reading this on GitHub, then you are looking at a mirror: its pull requests and issues
are not read. Please get in touch via email <contact.quantum@chalmersnextlabs.se> instead.

## Installation

Install using pip

```shell
pip install tergite
```

For pulse-level jobs written with [oqpy](https://github.com/openqasm/oqpy), and a backend's
frames as oqpy frames, install the `pulse` extra:

```shell
pip install 'tergite[pulse]'
```

## Dependencies

- [Python 3.13+](https://www.python.org/)
- [Qiskit 2.1+](https://github.com/Qiskit/qiskit)
- [Tergite Frontend](https://github.com/tergite/tergite-frontend), and a
  [Tergite Backend](https://github.com/tergite/tergite-backend) that runs circuits

## Provider Setup

- Ensure you have [Python 3.13+](https://www.python.org/) installed.

- Create an account with [QAL 9000](https://www.qal9000.se/) if you haven't already. (Or you can have your own [tergite Frontend](https://github.com/tergite/tergite-frontend) running)

- With the credentials received from Tergite, create and save a provider account by calling `Tergite.use_provider_account(..., save=True)`.

```python
from tergite import Tergite

provider = Tergite.use_provider_account(
    service_name="MY_SERVICE_NAME",
    url="https://api.qal9000.se",  # or the URL to your own tergite MSS,
    token="MY_API_TOKEN",
    save=True,
)
```

The code above stores your credentials in a configuration file called `tergiterc`, located in `$HOME/.qiskit` folder, `$HOME` being your home directory. Your token is stored in plain text, in a file only you can read (mode 600).

Once saved, you can retrieve this particular account using the `SERVICE_NAME` from anywhere in your code. From the provider, you can retrieve any backend you wish by name.

```python
provider = Tergite.get_provider(service_name="MY_SERVICE_NAME")

# display list of backends
print(provider.backends())

# access the 'Loke' backend
backend = provider.get_backend("Loke")
```

### Create a Throw-away Provider Account

- Alternatively, you can create a provider account that won't be saved. This is useful in things like automated tests. Just call the `Tergite.use_provider_account(account)` without the `save` option.

```python
from tergite import Tergite

# the account from before
provider = Tergite.use_provider_account( 
    service_name="MY_SERVICE_NAME",
    url="https://api.qal9000.se",  # or the URL to your own tergite MSS
    token="MY_API_TOKEN",
)
```

### Use an Account from the Environment

- Or set the environment variables `TERGITE_API_URL` and `TERGITE_API_TOKEN`, as Qiskit's IBM
  provider reads `QISKIT_IBM_URL` and `QISKIT_IBM_TOKEN`. They make an account named `env`, which
  is never saved, and which `Tergite.get_provider()` returns ahead of any saved account.

```shell
export TERGITE_API_URL="https://api.qal9000.se"
export TERGITE_API_TOKEN="MY_API_TOKEN"
```

```python
from tergite import Tergite

provider = Tergite.get_provider()
```

### On a Shared Computer

On a computer whose login others use too, such as a lab's guest account, anyone using that login
can read a saved token and run jobs with it: `Tergite.get_provider()` would even pick it for them.
There:

- do not save your account: use a throw-away account or the environment variables above;
- use an app token with a short lifespan, made for the session, and delete it in the dashboard
  when you are done.

## Running Circuits

A backend runs circuits transpiled to it: `transpile(circuit, backend)` maps them to the device's
qubits and to the gates its calibration provides, and `backend.run()` refuses a circuit with any
other gate. The backend compiles each circuit to pulses from its latest calibration.

```python
from qiskit import QuantumCircuit, transpile

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

job = backend.run(transpile(qc, backend), shots=1000)
print(job.result().get_counts())
```

`backend.run()` takes a circuit or a list of circuits, run as one job, and these options, which
`backend.set_options()` sets for every job:

| Option | Default | Values |
| --- | --- | --- |
| `shots` | 2000 | the shots of each circuit |
| `meas_level` | 2 | 2 for counts, 1 for each shot's IQ points (`job.result().get_memory()`) |
| `meas_return` | `"single"` | at `meas_level=1`, `"single"` for each shot's points or `"avg"` for their average |

Pulse schedules are no longer accepted, as Qiskit 2 has no `qiskit.pulse`: pulses are written
in OpenQASM 3's OpenPulse instead, below. `OpenPulseBackend` and `OpenQASMBackend` are deprecated
names of `TergiteBackend`.

## Running Pulses

A project an admin has allowed pulse-level jobs, in the dashboard, may send pulses to a device
that takes them, within the limits its operators set. They are
[OpenPulse](https://openqasm.com/language/openpulse.html), written by hand or with
[oqpy](https://github.com/openqasm/oqpy), on the frames the device publishes, e.g. `q00_drive`,
`q00_readout` and `q00_q01_coupler`; the backend checks each against the device's limits and
refuses it with the reason.

`backend.frames` gives those frames as oqpy frames, by name, and `backend.calibrations` the
`defcal`s of the device's gates, by gate and physical qubits, which play exactly what the gates do:

```python
import oqpy

frames = backend.frames
print(backend.calibrations[("x", (0,))])   # defcal x $0 { ... }
```

`backend.run(circuits, calibrations=[...])` runs a job's gates with `defcal`s of its own, as text
or an oqpy program, e.g. a gentler `x` on qubit 0:

```python
defcals = oqpy.Program()
gaussian = oqpy.declare_waveform_generator(
    "gaussian", [("amp", oqpy.complex128), ("d", oqpy.duration), ("sigma", oqpy.duration)]
)
with oqpy.defcal(defcals, oqpy.PhysicalQubits[0], "x"):
    defcals.play(frames["q00_drive"], gaussian(0.15, 40e-9, 10e-9))

job = backend.run(transpile(qc, backend), calibrations=[defcals])
```

`backend.run()` also takes programs of their own, as OpenQASM 3 text or an oqpy program, beside
circuits; a program's `cal` blocks play and `capture_v1` into classical bits. A job with a program
that does not measure runs at `meas_level=1`, its captures as IQ points, unless given another:

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
print(job.result().get_memory())          # each shot's IQ point
```

### Migrating from Pulse Schedules

A `qiskit.pulse` schedule that ran on the previous SDK is written again in oqpy, each channel
on the frame of the same name in `backend.frames`:

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

- **Durations are in seconds**, not samples: a sample is 1 ns, and a Drag's `beta`, which
  qiskit counts in samples, is in seconds too.
- **Waveforms** are OpenPulse's `constant`, `gaussian`, `gaussian_square`, `drag`, `sech` and
  `sine`, or arrays of samples (`oqpy.WaveformVar(samples)`), which reproduce any qiskit pulse
  exactly from its `get_waveform().samples`; qiskit lifts its Gaussians so their ends are zero,
  OpenPulse's do not.
- **An acquisition** becomes `measure`, with the device's calibrated readout, as above; or, for
  raw IQ points, a `capture_v1` in the `cal` block, which runs after a readout pulse on the
  same frame rather than alongside it.
- **A phase or frequency change** takes 4 ns of its frame, which qiskit counts as none.

- You can look at the [examples folder](./examples) for more samples.

## Examples and demos

This project has a long history with contributions of many different partners. 
All files in the `archive` folder are scripts from live demonstrations, which show the historical progression of the project.
Since research in quantum computing is moving fast, these files are meant to inspire and might not be functional with the source code of this library.

To find out how to use the library, please take a look into the notebooks and scripts inside the `examples` folder.

## ToDo

- [ ] Add docs and doc generation
- [ ] Convert archives into examples, adding proper credits and timestamps

## Contribution Guidelines

If you would like to contribute to tergite, please have a look at our [contribution guidelines](./CONTRIBUTING.md)

## Authors

This project is a work of [many contributors](https://github.com/tergite/tergite/graphs/contributors).

Special credit goes to the authors of this project as seen in the [CREDITS](./CREDITS.md) file.

## ChangeLog

To view the changelog for each version, have a look at the [CHANGELOG.md](./CHANGELOG.md) file.

## License

[Apache 2.0 License](./LICENSE.txt)

## Acknowledgements

This project was sponsored by:

- [Knut and Alice Wallenberg Foundation](https://kaw.wallenberg.org/en) under the [Wallenberg Center for Quantum Technology (WACQT)](https://www.chalmers.se/en/centres/wacqt/) project at [Chalmers University of Technology](https://www.chalmers.se)
- [Nordic e-Infrastructure Collaboration (NeIC)](https://neic.no) and [NordForsk](https://www.nordforsk.org/sv) under the [NordIQuEst](https://neic.no/nordiquest/) project
- [European Union's Horizon Europe](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en) under the [OpenSuperQ](https://cordis.europa.eu/project/id/820363) project
- [European Union's Horizon Europe](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en) under the [OpenSuperQPlus](https://opensuperqplus.eu/) project
