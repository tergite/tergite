# Running circuits

A backend runs circuits that are transpiled to it. `transpile(circuit, backend)` maps a
circuit to the device's qubits and to the gates its calibration provides; `backend.run()`
refuses a circuit with any other gate. The backend then compiles each circuit to pulses from
its latest calibration.

```python
from qiskit import QuantumCircuit, transpile

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

job = backend.run(transpile(qc, backend), shots=1000)
job.wait_for_final_state()
print(job.result().get_counts())
```

`backend.run()` takes one circuit, or a list of circuits that run as one job.

`job.result()` does not wait: it returns `None` until the job has finished. Call
`job.wait_for_final_state()` first, which polls every 5 s; pass `timeout=` in seconds to give up
sooner. A failed or cancelled job raises `JobFailedError` with its reason.

## Options

Pass them to `backend.run()`, or to `backend.set_options()` for every job after it.

| Option | Default | Values |
| --- | --- | --- |
| `shots` | 2000 | the shots of each circuit |
| `meas_level` | 2 | 2 for counts; 1 for each shot's IQ points (`job.result().get_memory()`) |
| `meas_return` | `"single"` | at `meas_level=1`: `"single"` for each shot's points, `"avg"` for their average |

## Pulse schedules

Pulse schedules are no longer accepted, as Qiskit 2 has no `qiskit.pulse`. Write pulses in
OpenQASM 3's OpenPulse instead: see [pulses.md](pulses.md).

`OpenPulseBackend` and `OpenQASMBackend` are deprecated names of `TergiteBackend`.
