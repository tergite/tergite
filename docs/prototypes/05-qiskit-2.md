# Step 5 sign-off: current Qiskit

A user acceptance test for step 5 of [REFACTOR.md](../../REFACTOR.md), with the setup of
[step 4's](04-circuits.md).

1. **The SDK installs beside current Qiskit.** In a fresh folder:

   ```bash
   uv init -q --python 3.13 && uv add -q /path/to/tergite "qiskit>=2.1"
   uv run python -c "import qiskit, tergite; print(qiskit.__version__)"
   ```

   It prints a 2.x version. The last release, pinned to Qiskit 1.2, cannot be resolved with
   `qiskit>=2.1`.

2. **Python 3.14 works too.** `UV_PYTHON=3.14 uv sync && uv run pytest --ignore=tests/e2e`
   passes; building symengine for 3.14 used to fail the install.

3. **Nothing deprecated is used.** `uv run pytest --ignore=tests/e2e` and
   `./dev/e2e_native_test.sh` pass with `filterwarnings` turning a `DeprecationWarning` into an
   error, and `tergite/compat` is gone.

4. **Results read as in Qiskit 2.** After step 4's circuit, `job.result().results[0].header`
   is a dict holding the circuit's `name`, `creg_sizes`, `memory_slots` and `metadata`, and
   `get_counts()` is as before.

5. **The performance checks hold.** `./dev/perf/record.sh /tmp/perf` and
   `compare.py dev/perf/baselines /tmp/perf` exit 0.
