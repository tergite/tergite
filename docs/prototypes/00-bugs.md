# Step 0 sign-off: the bug fixes

A user acceptance test for step 0 of [REFACTOR.md](../../REFACTOR.md). Part A needs no
server. Part B runs against the e2e stack. Each check says what should be seen.

## Part A: on your machine

1. **A fresh install works.** In an empty folder:

   ```bash
   uv venv -p 3.12 .venv && VIRTUAL_ENV=.venv uv pip install /path/to/tergite
   ```

   The install succeeds. Before step 0 it failed building `ibm-platform-services`.

2. **Importing is silent.** Point `HOME` at an empty folder and import:

   ```bash
   mkdir -p /tmp/uat-home && HOME=/tmp/uat-home .venv/bin/python -c "import tergite"
   ```

   Nothing is printed. Before step 0 it printed `Warning: No stored provider account found`.

3. **Saving an account works twice, into a missing folder, without a token.** With `HOME`
   still pointing at the empty folder:

   ```python
   from tergite import Tergite

   Tergite.use_provider_account("uat", url="http://old.example", save=True)
   Tergite.use_provider_account("uat", url="http://new.example", save=True)
   print(open("/tmp/uat-home/.qiskit/tergiterc").read())
   ```

   It prints one `[service uat]` section with `url = http://new.example` and no `token`
   line. Before step 0 the first call raised `FileNotFoundError`, and once the folder existed
   the second call raised `DuplicateSectionError`.

## Part B: against the e2e stack

Start the stack and keep it running, then open a Python container on its network, since
the backends' upload URLs use the stack's host names:

```bash
DEBUG=True FRONTEND_REPO=… BACKEND_REPO=… ./e2e_test.sh
docker run --rm -it --network tergite-e2e_tergite-e2e -v "$PWD":/app -w /app python:3.12-slim bash
pip install . && python
```

Use the `APP_TOKEN` from `e2e_test.sh`:

```python
from qiskit import QuantumCircuit, transpile
from tergite import Tergite
from tergite.exc import JobFailedError

provider = Tergite.use_provider_account("e2e", url="http://mss:8002", token="<APP_TOKEN>")
backends = provider.backends()
print([b.name for b in backends])
```

4. **Listing works and is honest.** The list prints. A device MSS sends in a shape the SDK
   cannot read is missing from it, with a `UserWarning` naming the device and its fields.

5. **Backends are hashable.** `print(len(set(backends)) == len(backends))` prints `True`.

6. **A cancelled job says so.**

   ```python
   backend = provider.get_backend("qiskit_pulse_2q")
   qc = QuantumCircuit(1, 1)
   qc.x(0)
   qc.measure(0, 0)
   job = backend.run(transpile(qc, backend), meas_level=2)
   job.cancel()
   job.wait_for_final_state()
   job.result()
   ```

   If the job was cancelled before it ran, `job.result()` raises
   `JobFailedError: Job … was cancelled: …` with the backend's reason. If it had already
   finished, it returns the counts. Before step 0 a cancelled job raised `RuntimeError:
   failed to GET memory of job`.
