# Step 4 sign-off: one backend, sending circuits

A user acceptance test for step 4 of [REFACTOR.md](../../REFACTOR.md), with the setup of
[step 1's](01-tests-and-tooling.md). tergite-backend's checkout must accept gate-level jobs:
`feature/gate-level-jobs`, merged into `sdk-refactor/e2e-combined` with its fixes.

1. **The e2e passes on circuits.** `./dev/e2e_native_test.sh` passes its 20 tests. The jobs it
   uploads hold OpenQASM 3, which `DEBUG=True` keeps in each backend's
   `temp-native/backends/<name>/storage/` folders.

2. **A circuit runs as Qiskit users expect.** Against the stack, in a Python shell:

   ```python
   from qiskit import QuantumCircuit, transpile
   from tergite import Tergite

   provider = Tergite.use_provider_account("e2e", url="http://127.0.0.1:8202", token="<APP_TOKEN>")
   backend = provider.get_backend("qiskit_pulse_2q")
   qc = QuantumCircuit(2, 2)
   qc.x(0)
   qc.measure([0, 1], [0, 1])
   job = backend.run(transpile(qc, backend), shots=200)
   job.wait_for_final_state(wait=0.2)
   print(job.result().get_counts())
   ```

   It prints counts that are mostly `01`. A circuit with `qc.h(0)` in it, run without
   transpiling it, raises `TergiteError: Backend 'qiskit_pulse_2q' has no h on qubits (0,):
   transpile the circuit … to the backend first`, and no job is registered.

3. **What went is gone.** `OpenPulseBackend(...)` warns that it is deprecated and makes a
   `TergiteBackend`; `backend.run(some_schedule)` raises that Tergite backends run circuits;
   `pip show tergite` lists neither h5py nor sympy among its requirements.

4. **The performance checks hold, the round trip included.** `./dev/perf/record.sh /tmp/perf`
   and `compare.py dev/perf/baselines /tmp/perf` exit 0, against the baselines this step
   records. Against those it replaced (`git show HEAD~1:dev/perf/baselines/…`), the client
   is much faster and its upload much smaller, by design, and the round trip, which now
   includes the backend's compilation, is no slower.
