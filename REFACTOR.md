# Refactor plan

Eleven steps, in order. Each numbered item is one commit, verified before the next. Steps 4 and 5
need tergite-backend to accept the gate-level payload (B2 below) in the stack the e2e runs
against; steps 0 to 3 do not wait for it. Step 8 needs pulse-level jobs (B6, F3, F4).

The SDK today is a Qiskit provider that turns circuits into pulse schedules on the user's
machine, from the calibration MSS publishes, and uploads them as a `PulseQobj` with sampled
waveforms. Qiskit removed pulse and Qobj in 2.0, so the SDK pins `qiskit>1,<1.3` and vendors
5,639 lines of Qiskit (`tergite/compat/`) to keep them. The backend then translates those
pulses back into quantify-scheduler operations. This plan moves the gate-to-pulse step to the
backend, where the calibration lives, and makes the SDK send OpenQASM 3: the same design
`tergite-qpu-driver` uses, built in tergite-backend's own code. The SDK then depends on
current Qiskit and nothing vendored, and its wire models come from the OpenAPI specs of MSS and
BCC instead of being transcribed by hand.

Pulse-level control, which Qiskit 2 has no `qiskit.pulse` for, returns as OpenQASM 3's own
pulse grammar, OpenPulse (D6), in the same payload. The plan ends with:

- **One wire format**, OpenQASM 3, for gates and, optionally with OpenPulse `defcal` and `cal`
  blocks, for pulses: one parser and one translator into quantify-scheduler on the backend.
- **An SDK on current Qiskit** with nothing vendored and no pulse compilation of its own: it
  sends circuits or pulse programs, and offers the device's frames and gate calibrations.
- **Gate pulses in one place**, the backend's calibration-driven elements (the CZ in its
  `CouplerEdge`), which a job's `defcal` may override; the qobj path, with the `wacqt_cz`
  waveforms the SDK sampled, deleted (B5).
- **Simulators that play quantify's pulses on QuTiP** (B3): gate-level and pulse-level jobs
  alike, through the same compilation as a chip, and so neither the end-of-life
  qiskit-dynamics nor `qiskit~=0.45` left in the backend, nor the conflict between its
  extras: one package per OS and architecture, a config choosing chip or simulator.
- **Pulse access opt-in per project**, granted by an admin in the dashboard (F3), and guarded
  by the backend (B6).

## Decisions to confirm

Each has a recommendation; the plan is written as if it were taken.

- **D1. OpenPulse goes.** Qiskit 2 has no `qiskit.pulse`, so pulse schedules cannot be a user
  input on current Qiskit. Users submit circuits; pulse-level work is the calibration's, on
  the backend. `OpenPulseBackend` and `OpenQASMBackend` become one `TergiteBackend`, with the
  two names kept as deprecated aliases for one release.
- **D2. `get_provider(name)` raises for an unknown name.** Today it silently returns the first
  saved provider (`types/provider_factory.py:103`), which `test_get_provider_non_existing`
  pins, so a typo sends jobs to another service. `get_provider()` without a name still
  returns the first.
- **D3. The backend's simulators play the pulses quantify compiles, on QuTiP.** The
  `qiskit_pulse_1q`/`2q` simulators already simulate pulses, but through `qiskit.pulse` and
  qiskit-dynamics, which pin the backend to `qiskit~=0.45`, and so to a numpy older than the
  quantify extra's; hence the two conflicting extras, and a binary for each. Recommended: a
  simulator is the quantify executor with QuTiP in the Qblox clusters' place. A job compiles
  as on a chip, gates through the device's elements and `defcal`s, `cal` blocks as they are,
  against a `QuantumDevice` of the simulated chip's calibration; the device-level schedule's
  pulses are sampled per port and clock and drive the Hamiltonians the dynamics backends
  have today (transmons, a tunable coupler, from the calibration), integrated once per circuit
  with T1/T2 loss. Shots are sampled from the final state; for `meas_level=1`, IQ points
  around the calibrated discriminator's centroids, so the e2e's clustering tests keep a
  meaningful input. So the gate-to-pulse translation is tested without hardware, pulse-level
  jobs can be tried before hardware time, and one dependency set ships both. Its cost: about
  0.2 s a circuit for a qubit and 0.65 s for two and a coupler (the round trips of today's
  simulators, less Loke's), growing exponentially, so simulated chips stay at two or three
  qubits; the Qblox hardware compilation (sequencers, NCOs, LOs) is not exercised. qiskit-aer
  was the alternative: milliseconds and 15 to 20 qubits, but gates only, a second path to
  keep, and no test of the pulses.
- **D4. `Provider.job(job_id)` rebuilds a result from MSS, not from the HDF5 logfile.** Today
  it downloads the logfile only to read the qobj back out of it, the one use of `h5py`.
  Recommended: MSS's `JobResult` gains optional `shots`, `meas_level` and per-circuit
  `name`/`num_clbits` (F1), so the SDK keeps no payload to rebuild a result from.
- **D5. One coordinated release.** The SDK and the backend of one release move to the new
  payload together: the SDK sends only OpenQASM 3, and the backend takes only it, its qobj
  path deleted in the same release (B5, D7).
- **D6. Pulse level is OpenQASM 3 with OpenPulse, opt-in per project, guarded by the
  backend.** A job's OpenQASM may carry `defcal` blocks, which replace a gate's pulses within
  that job, and `cal` blocks, which play pulses on the frames the device publishes. Only a
  project an admin granted pulse access, in the dashboard, may send them; the backend
  enforces limits its operators set per device, and refuses pulse programs on a device
  without them. The SDK writes no pulses itself: users write them with `oqpy`, Amazon
  Braket's library for OpenQASM 3 with OpenPulse, or by hand.
- **D7. The qobj path goes in the release that brings pulse-level jobs**, not a release
  after: few use the system yet, so an older SDK that stops working the day the backend
  upgrades costs less than keeping a second payload, and the code behind it, for a release.
  Pulse users move to OpenPulse with step 9's script and guide.

## What the other repos do first

Each of these belongs in that repo's own plan; the SDK steps name the one they need.

| Id | Repo | Change |
| --- | --- | --- |
| B1 | tergite-backend | Commit its OpenAPI spec as MSS does: `dev/openapi/export.py` writes `dev/openapi/openapi.json`, every route declares its response, and `tests/test_openapi.py` fails when the file is stale. |
| B2 | tergite-backend | `POST /jobs` also accepts the gate-level payload below. The heavy worker parses each circuit with `qiskit.qasm3`, maps each instruction to quantify-scheduler gate-level operations (`Rxy`, `Rz`, `CZ`, `Measure`, `Reset`, `IdlePulse`; CX, SWAP and the rest decomposed into them) and compiles the schedule with `SerialCompiler` against a `QuantumDevice` built from the backend's calibration. Pulses are then quantify's parametric ones (DRAG from `amp180`/`motzoi`/`duration`, dispersive measurement, square CZ), sampled on the backend. It follows `tergite-qpu-driver`'s design, without depending on qpi. Results keep today's `Job.result.memory` shapes, with clbits ordered as Qiskit orders them (clbit 0 rightmost). |
| B3 | tergite-backend | The simulators per D3, after B6: a QuTiP runner behind `QuantifyExecutor` beside the clusters, sampling the device-level schedule's pulses (quantify's own waveform functions) per port and clock into the drive of each qubit's and the coupler's frame, with the simulated chip's Hamiltonian parameters and the drive strength per unit of amplitude beside its calibration in the backend config. Simulated devices take pulse-level jobs within their own `pulse_limits`, lifting B6's refusal, and publish frames and defcals as a chip does. Deleted with qiskit-dynamics: the qiskit executor, `qiskit/circuits.py`, the `WacqtCZPlay` that B5 left in `qiskit/instruction.py`, the dynamics backends, `qiskit~=0.45` and `jax`. The `qiskit` extra and the extras' `conflicts` go: QuTiP 5 takes numpy 2, so one dependency set, one `bcc` binary per OS and architecture in place of `bcc` and `bcc.simulator` (GitLab's and GitHub's package jobs), and the backend config chooses clusters or simulator. The e2e runs every backend from one process. |
| B4 | tergite-backend | `Device.basis_gates` lists the gates B2 compiles, and `DeviceCalibration` keeps the durations and errors the SDK's `Target` reads: `pi_pulse_duration`, `readout_assignment_error`, the resonator's pulse and integration times, and T1/T2. |
| B5 | tergite-backend | With B6, in the same release (D7): delete the `PulseQobj` path, `libs/qiskit/`, the vendored Qobj encoder and decoder, `PulseLibInstruction`, and the qobj translator into quantify (`quantify/instruction.py`, the channel registry). |
| B6 | tergite-backend | Pulse-level jobs (D6), each item one commit: (1) one parser for every job, `openpulse`'s, which reads plain OpenQASM 3 too: gates translate as B2 has them, gate definitions in the program are inlined, and the quantify extra no longer needs Qiskit; (2) `defcal` blocks replace a gate's pulses within the job, and `cal` blocks translate into quantify operations on the published frames: `play` of an allow-list of waveforms (gaussian, drag, constant, gaussian_square, and bounded sample arrays), `shift_phase`, `set_phase`, `shift_frequency`, `set_frequency`, `delay` and `capture`; (3) each device's frames, a drive, a readout and each coupler's flux, named after its ports and at their calibrated frequencies, and its gates' calibrations as OpenPulse `defcal`s, sent to MSS with its calibration (F4); (4) the guardrails: per-device limits in the backend config (amplitude per kind of port, how far a frame may move from its calibrated frequency, energy and duty cycle per shot and per job, program duration, waveform samples, capture length), checked at upload with the reason for a refusal, and the pulse-access claim of the job token (F3); a device without limits refuses pulse programs; (5) the simulators refuse pulse programs. `dev/check_gate_level.py` checks the limits are set. |
| F1 | tergite-frontend | MSS's `JobResult` gains the optional fields of D4, which the backend fills in its `job_updated` event. |
| F2 | tergite-frontend | `ui/fixtures` gain a project with no QPU seconds left and an app token for it, which this repo's e2e uses to check MSS's quota refusal (step 1.7). Its other fixtures, MSS's config and the backends' settings and keys, the e2e already reads from the frontend checkout. |
| F3 | tergite-frontend | Pulse access per project (D6): the project model gains `is_pulse_allowed`, off by default; MSS signs it into the job token it gives the backend; admins grant and revoke it in the dashboard's project forms (`admin-projects`), the projects page shows it, and a project's members request it as a new request type, `project-pulse-access`, beside `project-qpu-seconds` (`services/requests`), which admins approve in `admin-requests`. `ui/fixtures` gain a project with it and an app token, for this repo's e2e (step 8). |
| F4 | tergite-frontend | MSS's `DeviceCalibration` gains the device's frames and its gates' `defcal`s, optional, which the backend sends with its calibration (B6.3) and the SDK reads (step 8). |

**The gate-level payload**, uploaded to the `upload_url` as today's multipart `upload_file`.
Its shape follows qpi's `JobPayload` on purpose, so the two stacks read alike:

```json
{
  "job_id": "…",
  "params": {
    "circuits": [{"name": "bell", "qasm": "OPENQASM 3.0; …", "num_clbits": 2, "metadata": {}}],
    "shots": 1024,
    "meas_level": 2,
    "meas_return": "single"
  }
}
```

**A pulse-level job** (B6) is the same payload, its `qasm` an OpenQASM 3 program with OpenPulse
blocks on the frames the device publishes, e.g. a job's own pulses for `x`:

```
OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
    extern gaussian(complex[float[64]], duration, duration) -> waveform;
}
defcal x $0 {
    play(q00_drive, gaussian(0.25, 80ns, 20ns));
}
bit[1] c;
x $0;
c[0] = measure $0;
```

## Conventions

The code reads like an article: the overview first, the detail below it. These are the
conventions of tergite-frontend's `DESIGN.md`, adapted to a library; every step applies them to
the code it touches, and step 7 moves them into this repo's own `DESIGN.md`.

1. **A function is a composition of functions.** A public function's body is a short sequence
   of calls, each to a function that does one thing and is named for it. Each step is built
   the same way until it is a single operation.
2. **Two exceptions.** Do not extract a step that would be a one-line function. Do not split a
   performance-critical path where the extra calls cost something measurable.
3. **Callees sit below their callers.** A file runs: constants, public functions in the order
   a caller uses them, then private helpers in the order they are first called.
4. **A comment that labels a phase is a missing function.** `# capture circuit-level classical
   register metadata` becomes the name of the function that does it.
5. **Data is a struct; state gets a class.** Data is a Pydantic model, a frozen `@dataclass`,
   an `Enum` or an `Exception`; its only methods are derived views of its own fields and
   `from_*`/`to_*` conversions. What owns state across calls (an HTTP client, a backend's
   cached target, a job's last-known status) is a class. Qiskit's base classes are the one
   place we inherit: `TergiteBackend(BackendV2)` and `Job(JobV1)` are the contract users
   program against.
6. **Stateless behaviour is a module-level function**, taking explicit arguments and returning
   data, the HTTP client first when it does I/O. No `Protocol` or ABC with one implementation,
   no inheritance used to share behaviour.
7. **Dependencies arrive as arguments.** Importing `tergite` does no I/O and prints nothing.
   The `Provider` owns its HTTP client and hands it to the functions that call the API; no
   function reads `~/.qiskit/tergiterc` except the accounts module, when asked to.
8. **One home per kind of thing.** HTTP lives in `tergite/api/`. Errors subclass
   `tergite.exc.TergiteError`. The public surface is `tergite/__init__.py`, with `__all__`.
   Development and test tooling (the OpenAPI generator, the e2e runner) lives in `dev/`.
9. **A reputable library beats our own code, and nothing is vendored.** When Qiskit removes
   something, we stop needing it rather than copy it. The commit that adds our own code says
   why no library did the job.
10. **A name says what the thing is.** Variables are nouns that name their content, functions
    are verbs, booleans start with `is_`/`should_`, and no function is named `build_*`.
11. **Obvious beats clever.** An `if`/`else` returning each whole literal, one explicit `if`
    per optional field; not loops over tuples of fields or helpers returning two things to
    pull apart.
12. **The wire is generated, not transcribed.** Models of what MSS and BCC send and receive
    come from their committed OpenAPI specs (step 2), so a change on either side fails a test
    here, not a user's job.
13. **A value that is only defined stays where it is used.** No function that only returns a
    literal.
14. **The public API holds.** `Tergite.use_provider_account`, `Tergite.get_provider`,
    `provider.backends`, `provider.get_backend`, `provider.job`, `backend.run`,
    `backend.target`, `backend.set_options`, `job.status`, `job.result`, `job.cancel`,
    `job.download_url` and `job.logfile` keep their signatures. A break happens only where a
    decision above says, with a `Changed` changelog entry and, where it can, a deprecation
    warning for one release.
15. **Unchanged:** the Apache 2.0 licence header on every file, with a line per contributing
    party; constants at the top; no banner comments; Google-style docstrings saying what a
    function does for its caller; comments only for what the code cannot say.

**Every commit is verified the same way:** `black` and `isort` with no flags, `pyflakes tergite
tests dev`, then `pytest > "$LOG" 2>&1; echo "exit=$?" >> "$LOG"`. `dev/e2e_native_test.sh`
(step 1.6) runs on every merge request in CI, and locally at the end of steps 1, 4, 5 and 6.
`tests/test_styleguide.py` (step 1.5) has a
baseline of the violations that existed when it was added; a commit that fixes one deletes its
line, and no commit adds one.

**Every step ends with a sign-off.** Its last commit adds `docs/prototypes/<NN>-<step>.md`: a
script a user or an agent runs against the e2e stack (install, submit the example circuits,
what should come back). From step 1 on, the sign-off also reruns `dev/perf/record.sh` and
`compare.py` (step 1.9), and the go-ahead is given before the next step starts.

## Step 0: fix the bugs

The only behaviour changes outside the decisions. Each commit adds a test that fails before the
fix and gets a `Fixed` changelog entry.

1. **A fresh install fails.** `qiskit-ibm-runtime` pulls in `ibm-platform-services`, whose
   build needs `pkg_resources`, which current setuptools no longer has. Nothing imports
   `qiskit_ibm_runtime` (its models are vendored in `compat/`), and nothing imports `pandas`:
   both leave `pyproject.toml`. `sympy`, imported by `device_compiler`, is declared until
   step 5 deletes it.
2. **Any device with `open_pulse = false` breaks `provider.backends()`.** `OpenQASMBackend`
   (`types/backend.py:607`) never implements the abstract `device_properties`, so building
   it raises `TypeError`, and `Job.submit` (`types/job.py:134`) refuses the `QasmQobj` it
   would make anyway. Until step 4 merges the two, it gets `device_properties = None`, and its
   `run` raises a `TergiteError` saying the backend accepts pulse jobs only.
3. **Backends are unhashable.** `OpenPulseBackend` defines `__eq__` (`:590`) without
   `__hash__`, which makes Python drop the inherited one, and that one (`:268`) reads a
   `backend_name` no backend has. Hash on `(name, backend_version)`, fields `__eq__` compares,
   defined once on the base class, and delete the copies of `meas_map`, `last_calibrated`, `coupling_map`,
   `_default_options`, `_as_dict`, `__repr__` and `__eq__` that `OpenPulseBackend` repeats.
4. **`save=True` fails twice over.** It raises `FileNotFoundError` when `~/.qiskit` does not
   exist, and `DuplicateSectionError` when the service name is already saved
   (`services/configs/__init__.py:100`), so running the README's snippet a second time
   crashes. Create the folder, and replace the section.
5. **`import tergite` reads `~/.qiskit/tergiterc` and prints** (`types/provider_factory.py:40`),
   at import time. The factory loads the file on first use. Its "no stored account" warning
   goes, as `get_provider` raises when there is none, and the invalid-account one at
   `configs/__init__.py:67` goes through `warnings.warn`. The `print` in `backend.run` (`:179`)
   becomes a `logging.info`.
6. **No HTTP call has a timeout** (`services/api_client/__init__.py:69-258`), so a backend
   that accepts the connection and never answers hangs the user's session for good. Every
   call gets one: 30 s, and 300 s for the upload and the logfile download.
7. **`job.result()` on a failed or cancelled job** raises "failed to GET memory" rather than
   the job's `failure_reason` or `cancellation_reason`, and builds every `Result` with
   `success=True` (`types/job.py:250, 255`). It raises a `JobFailedError` carrying the reason.
8. **A malformed device disappears without a word** (`api_client/__init__.py:79`). It is still
   skipped, as `test_get_malformed_backend` pins, but with a warning naming the device and the
   fields that failed validation.
9. **The logfile is copied from `response.raw`** (`api_client/__init__.py:237`), which skips
   decoding, so a response sent with `Content-Encoding: gzip` is saved compressed and `h5py`
   cannot open it. Not reproduced: neither BCC nor MSS compresses a response, so nothing in
   the stack sends one. Left to step 3, whose httpx client decodes what it reads.

## Step 1: pin behaviour with tests, and the tooling to run them

Tests and tooling only. After this step, a refactor commit that changes behaviour fails a test.

1. **The public API contract** (convention 14). Every name in it has a test of its signature
   and behaviour in `tests/integration/`, against the mocked API; most exist already.
2. **Golden results.** For `meas_level` 1 and 2, the `Result` of: a Bell pair measured into
   `c`, `measure_all()`, a partial measurement, measurements into permuted clbits, and two
   circuits in one job. These pin what `normalise_classical_registers` and the
   `header.metadata.tergite` patching do today, so step 4 can delete both and prove the
   gate-level path gives the same counts and memory.
3. **uv for everything a contributor or CI runs**, as tergite-frontend and tergite-backend do;
   end users still `pip install tergite` (or `uv add tergite`) from PyPI. One commit per
   surface:
   - **The project.** `uv.lock` committed; the dev and test extras become one `dev`
     `[dependency-groups]` group, so they stop shipping as installable extras. The setuptools
     build backend stays.
   - **Python as the rest of the stack has it:** `requires-python = ">=3.13"`, as in
     tergite-frontend and tergite-backend, with `UV_PYTHON` in CI; like them, no
     `.python-version` is committed. Users on 3.12 keep
     the last release that supports it; a `Changed` changelog entry says so, and the README's
     dependencies list says 3.13.
   - **Local development.** CONTRIBUTING's conda, `python -m venv` and `pip install .[test]`
     instructions become `uv sync` and `uv run pytest`.
   - **CI.** GitLab and GitHub install uv and run `uv sync --locked`, then `uv run` for the
     linters and pytest, on Python 3.13 alone, with `UV_PYTHON: "3.13"` in the release jobs,
     as the other two repos do. The `apt install libopenblas-dev gfortran` steps, needed
     today only on 3.13 for packages that ship no wheel, go if the locked wheels need no
     build, which `uv sync --locked` shows.
   - **Releases.** `uv build` and `uv publish` replace `pip install build twine`. That also
     fixes two broken release steps. GitLab's staging upload passes `r` where it means `-r`
     (`.gitlab-ci.yml:113`), so twine takes `r` for a file and never reaches TestPyPI.
     GitHub's "Deploy docs" sources a `.venv` that nothing creates and runs `mkdocs`, which
     nothing installs, for a `mkdocs.yml` the repo does not have; it is deleted. The
     release regenerates `uv.lock` with the version bump, as tergite-backend's does.
   - **The e2e.** `dev/e2e_native_test.sh` (item 6) installs with `uv sync` and starts MSS
     and the backends with `uv run`.
4. **Lint the whole tree.** `black`, `isort` (`profile = "black"`) and `pyflakes` over
   `tergite tests dev`, in GitLab CI and GitHub Actions alike; GitHub's lint stops depending
   on `SHOULD_LINT`.
5. **`tests/test_styleguide.py`**, ported from tergite-frontend's: verbs for functions, no
   `build_*`, no banner comments, licence headers, `__all__` in `tergite/__init__.py`, with a
   baseline of today's violations.
6. **A native e2e, off Docker**, as tergite-frontend's `dev/e2e_native_test.sh` already is.
   Today `e2e_test.sh` clones both repos, builds their images, starts them with Docker
   Compose, and runs the tests in another container, because the backends' upload URLs
   name hosts on the Docker network; outside Docker, `tests/e2e/conftest.py` patches
   `requests` to rewrite those hosts. The new `dev/e2e_native_test.sh`:
   - runs MSS from `FRONTEND_PATH`, or a clone of `FRONTEND_REPO` at `FRONTEND_BRANCH`, on a
     MongoDB of its own, seeded with MSS's `dev/seed.py`. MSS's config, the backends'
     settings and keys and the seeded users, projects and tokens all come from the
     frontend's `ui/fixtures`, which its own e2e keeps in step with MSS and the backend, so
     this repo keeps no copy to drift;
   - runs the backends from `BACKEND_PATH`, or a clone, with `main.py start`, so their
     workers execute jobs: `qiskit_pulse_1q` and `qiskit_pulse_2q` in one process, from the
     backend's qiskit extra, and Loke on a dummy Qblox cluster in another, from its quantify
     extra, as the two extras conflict. Loke's settings, quantify and calibration configs
     stay in this repo: the frontend's Loke has 8 qubits and is never recalibrated, as its
     e2e runs no worker;
   - binds everything to 127.0.0.1, so the upload URLs work as they are and the proxy in
     `tests/e2e/conftest.py`, `is_in_docker` and `IS_IN_DOCKER` go;
   - keeps its data in `temp-native/`, fresh each run, keeps the services up with
     `DEBUG=True`, and passes its arguments to `pytest`, so one test can be run;
   - replaces `e2e_test.sh`, `e2e-runner.sh`, `tests/fixtures/e2e-runner.sh` and the
     fixtures only Docker used (the Compose file, `mongo-init.js`, `e2e.env`, MSS's config,
     the backends' settings, seeds, keys and booking databases), and runs in CI on every
     merge request, on `main` and on tags, rather than by hand.
7. **More of the SDK in the e2e.** Today it has four tests: one circuit on each simulator, IQ
   points on one, and the dummy quantify device. Each public name of convention 14 gets an
   e2e test against the real stack, one file per area:
   - **Providers and backends:** listing, `get_backend`, an unknown name, and a target whose
     gates and properties match the seeded calibration.
   - **Running:** both simulators at `meas_level` 1 and 2, `meas_return` single and avg,
     several circuits in one job, and the golden cases of item 2 (Bell pair, `measure_all`,
     partial, permuted clbits), so step 4 proves on the real stack that the gate-level path
     answers as the pulse path did.
   - **Jobs:** status through to done, cancelling a queued job, `provider.job(job_id)` from a
     new provider, the logfile download, and `JobFailedError` for a job the backend fails.
   - **Auth and quota:** an unknown, an expired and an inactive project's app token are
     refused, with the seeded tokens; once F2 lands, a project with no QPU seconds left
     cannot submit (MSS's 403).
8. **Fast tests, as tergite-frontend's went from about 45 minutes to 1.** First record where
   the time goes: `pytest --durations=25`, for the unit suite and for the e2e, with the
   numbers in the commit. Then, one commit per trick, each with its before and after:
   - **The stack starts once per e2e run**, and every test shares it. Nothing restarts
     between tests, and nothing resets: a test only adds jobs, which no other test reads,
     and a test that needs a state of its own gets its own seeded project and token.
   - **Poll fast.** `wait_for_final_state` polls every 5 seconds by default; the e2e passes
     `wait=0.2`.
   - **Session-scoped fixtures** for what tests read but never change: the provider, the
     backends, the calibrations and the transpiled test circuits.
   - **One job, several circuits**, where tests check the same thing on different circuits,
     so the backend's per-job cost is paid once.
   - **Cut the parametrizations that cross axes that do not interact**, as MSS's did:
     `_INVALID_PARAMS` runs every auth test for 4 backends × 4 tokens; one route per test is
     enough. A case that behaves alike on every backend runs on one, with one smoke case on
     each other.
   - **`pytest -n 4 --dist=worksteal`** for the unit suite, if the durations show it pays;
     the e2e stays serial, since the backend runs one job at a time.

   The target is the e2e under two minutes once the services are up, and the unit suite
   under ten seconds.
9. **Performance checks**, so no refactor step makes the SDK slower. `dev/perf/`, as in
   tergite-frontend: `record.sh <dir>` records, the baselines live in `dev/perf/baselines/`,
   and `compare.py dev/perf/baselines <dir>` exits 1 when a measure is more than 10%, and
   more than its noise floor, worse.
   - **The client alone**, against the mocked API, with pytest-benchmark: the time to
     `import tergite`; `provider.get_backend` (time and HTTP calls; today it makes one call
     per characterized device, step 6.3); building a target; `backend.run` up to the upload
     (time and payload bytes); `job.result()` for 1, 10 and 100 circuits of 10,000 shots;
     and peak memory for each, from `tracemalloc`.
   - **The round trip**, against the native stack of item 6: `dev/perf/test_roundtrip.py`,
     which `record.sh` runs through `dev/e2e_native_test.sh` with `PYTEST_TARGET`. Five jobs
     of each kind (one and two qubits, counts and IQ points, Loke) from `run()` to
     `result()`: p50 and p95 latency, jobs per minute, the HTTP calls `run()` and `result()`
     make (the status polls between them vary with timing, so they are left out), the
     bytes uploaded, and the CPU time and peak memory of the SDK, MSS and backend
     processes, children included, sampled with psutil.
   - **HTTP calls are compared exactly**: one call more is a regression, whatever the
     timings say.
   - The baselines are recorded at the end of this step, of the code after step 0 and
     before any refactor commit, and every sign-off reruns the checks. Step 4 changes the
     payload and moves compilation to the backend by design. Its sign-off holds the round
     trip to the baseline, and records new baselines for payload size and client time,
     with the reason in the commit. Compare only runs made on the same machine.
10. **Housekeeping.** Check `examples/` runs against the e2e stack, which step 7 then
    updates. `archive/` stays: it was reintroduced on purpose in 0.1.1, as the history of the
    live demos, and only the user decides it goes.

## Step 2: the wire contract, from OpenAPI

1. **MSS.** `dev/openapi/mss.json` is a copy of tergite-frontend's `dev/openapi/openapi.json`
   at the release the SDK targets. `dev/openapi/generate.py` runs datamodel-code-generator on
   it into `tergite/api/mss_models.py`, keeping only the schemas the SDK reads (`Device`,
   `DeviceCalibration` and its parts, `JobCreate`, `CreatedJobResponse`, `Job`, `JobResult`,
   `JobStatus`). `tests/test_openapi.py` fails when the generated file no longer matches the
   spec, and `dev/openapi/sync.sh` copies the spec from `FRONTEND_PATH`.
2. **BCC**, once B1 lands: the same for `dev/openapi/bcc.json` into
   `tergite/api/bcc_models.py`, for the upload, cancel and logfile routes.
3. **The hand-written DTOs go.** `services/api_client/dtos.py` is replaced by the generated
   models, apart from the derived views `TergiteBackendConfig.model_post_init` computes
   (`coupled_qubit_idxs`, `qubit_ids_coupler_dict`), which become functions beside their one
   user. `JobFile` stays hand-written until B1 publishes the upload body's schema.
4. **The e2e checks the copy.** `dev/e2e_native_test.sh` runs `dev/openapi/check_served.py`
   against the MSS and the backend it starts, and fails when they serve, of the schemas the
   SDK reads, any that differ from the pinned copies: the rest, such as MSS's
   `/auth/{provider}` routes, follow the service's config.

## Step 3: one HTTP client

1. **`tergite/api/`** replaces `services/api_client/`. `client.py` makes the two
   `httpx.Client`s a `Provider` owns: MSS's, with its base URL and the account's app token,
   read for each request so that a token changed on the account is used, and the backends',
   to which each job gives its URL and token; both with timeouts and one shared SSL
   context, as loading the CA certificates made each client cost 6.7 ms. One
   `raise_for_error` raises an `ApiError(message, status_code)` from the `{"detail": …}`
   body. `mss.py` holds `get_devices`, `get_calibration`, `create_job` and `get_job`;
   `bcc.py` holds `upload_job`, `cancel_job` and `download_logfile`, each taking the client
   first and returning generated models. Done as one change with items 2 to 4, which it
   brings with it.
2. **`tergite/exc.py`**: `TergiteError`, `ApiError`, `JobFailedError`,
   `BackendNotFoundError` (a `QiskitBackendNotFoundError` too, so existing `except` clauses
   still catch it). Every `RuntimeError` and bare `Exception` the package raises today becomes
   one of these.
3. **The upload is made in memory.** `send_job_file` writes the job to a temporary file only
   to read it back (`api_client/__init__.py:157-185`); httpx sends the bytes.
4. **`requests` leaves**, and `requests-mock` with it; the tests mock with `respx`.

## Step 4: one backend, sending circuits

Needs B2 and B4 in the e2e stack.

1. **`tergite/target.py`**: `get_target(device, calibration) -> Target`, pure and
   table-tested. Its gates are the ones B2 compiles on every device: rz, sx, x and rx on
   each qubit, cz on each coupled pair whose coupler is calibrated, and measure, reset and
   delay, each with an `InstructionProperties` duration and error from the calibration,
   and `qubit_properties` from its T1, T2 and frequency. No schedules. `device.basis_gates`
   is not read: today's devices list their gate configs there (`['x']`, `['u', 'h', 'x']`),
   from which the transpiler could not even make an H.
2. **`tergite/backend.py`**: one `TergiteBackend(BackendV2)`. `run(circuits, **options)` checks
   each circuit uses only the target's instructions, writes it with `qiskit.qasm3.dumps`,
   registers the job at MSS and uploads the gate-level payload. Options: `shots`,
   `meas_level`, `meas_return`. `OpenPulseBackend` and `OpenQASMBackend` remain as aliases
   that warn (D1).
3. **`tergite/results.py`**: `get_result(job, circuits) -> Result`, pure: counts and memory per
   circuit from `Job.result.memory`, with the clbit widths the circuits carry. The golden
   results of step 1.2 pass unchanged.
4. **Delete the patching the qobj needed:** `utils/quantum_circuit.normalise_classical_registers`,
   `extract_q_to_clbit_map`, `utils/qobj.derive_reg_len_from_qobj_experiment`,
   `rewrite_acquire_memory_slots` and the `header.metadata.tergite` keys. The backend reads
   the clbits from the QASM.
5. **`provider.job(job_id)`** builds its job from MSS's alone, so `utils/job_file.py` and
   `h5py` leave the SDK's dependencies (the tests keep h5py). MSS does not keep how a job was
   run, so its measurement level and shots are taken from the memory, and its counts come
   without register names or leading zeros; F1 would give them back. `job.logfile` still
   downloads the file. Counts now keep a classical register a circuit never measures into,
   as Qiskit's own backends do, where the qobj patching dropped it.

## Step 5: current Qiskit

1. **Delete what only the pulse path used:** `tergite/compat/` (the vendored Qobj, assembler,
   disassembler, pulse instruction converters and IBM runtime models, 5,639 lines),
   `services/device_compiler/` (573 lines, with the unused numpy `delta_t_function`) and
   `utils/qobj.py`. `sympy` leaves `pyproject.toml`.
2. **`qiskit>=2.1,<3`**, at the latest 2.x when the step lands (tergite-qpu-driver already
   resolves 2.5). The tests' `DeprecationWarning` count is zero, and `pytest` turns one into an
   error from here on.
3. **Python stays `>=3.13`** (step 1.3), and `tests/e2e` runs on the same version as MSS and
   the backends it starts.

## Step 6: accounts and the provider

1. **`tergite/accounts.py`**: `load_accounts(rc_file)` and `save_account(rc_file, account)`,
   functions over an `Account` model, replacing the `Tergiterc` class, which holds a parser
   only to write it back. The file format stays.
2. **`ProviderFactory`** keeps its methods, loads the rc file on first use (step 0.5), and
   `get_provider` raises for an unknown name (D2).
3. **The provider stops caching forever.** `available_backends` is a `cached_property`, so a
   long session never sees a device come online. `backends()` fetches the devices each call;
   a backend refreshes its target when MSS reports a newer `last_calibrated` than the one it
   was built from. `get_backend(name)` fetching the calibration of every characterized device was
   fixed in step 1, as the native e2e showed one device's incomplete calibration failing
   every `get_backend()`; filtering by other criteria than the name still builds targets.
4. **Long functions become compositions**, one per commit, with unit tests for the pure steps:
   every function still over 30 lines once steps 3 to 5 have landed. As built: none was. The
   longest bodies, docstrings aside, are `TergiteBackend.run` (29 lines), `Job.result` and
   `get_result` (28): each a flat run of guard clauses or one constructor call, which splitting
   would make no clearer, so none was split.

## Step 7: docs

1. **`DESIGN.md`**: what the SDK is, its place in the stack (MSS for devices, calibrations and
   jobs; BCC for the upload and the logfile), the job flow, the package layout, the wire
   contract and how it is regenerated, testing, CI and releasing, and these conventions.
2. **README and CONTRIBUTING**: Qiskit 2, `transpile(circuit, backend)` before `run`, the
   options, no OpenPulse; the contact address matches tergite-frontend's.
3. **`examples/`**: the notebooks and `hello_world.py` run against the e2e stack, and
   `tests/e2e` executes `hello_world.py`.

## Step 8: pulse-level jobs

Needs B6, F3 and F4 in the stack the e2e runs against.

1. **`backend.run` takes pulse programs**: OpenQASM 3 text, or anything with `to_qasm()`, such
   as an `oqpy.Program`, sent as a circuit's `qasm` as it is; the SDK does not check pulses,
   which the backend does with the device's limits, and runs them at `meas_level` 1, or 2
   where the program measures.
2. **`backend.run(circuits, calibrations=[...])`** puts the `defcal`s given, as text or `oqpy`,
   into each circuit's OpenQASM, after a `defcalgrammar "openpulse";`, so that a job runs its
   own pulses for a gate.
3. **`backend.frames` and `backend.calibrations`**: the device's frames as `oqpy` frames, and its
   gates' `defcal`s, both from the calibration MSS serves (F4); `oqpy` is the `pulse` extra, so
   that gate-level users do not install it.
4. **e2e on Loke's dummy clusters**: a job with its own `defcal x`, a `cal` block that plays and
   captures, and the refusals: a project without pulse access (F3's fixture) and a pulse beyond
   the device's limits; and, on a simulator (B3), the same `defcal x` and a Rabi amplitude
   sweep in `cal` blocks, whose counts show the physics the dummy clusters cannot. The
   performance checks hold.

## Step 9: from OpenPulse schedules to OpenQASM 3

1. **A migration script**, `examples/migration/schedule_to_openpulse.py`, run with Qiskit 1.x: it
   turns a `qiskit.pulse` `Schedule` into an `oqpy` program, channel to frame as the backend's
   qobj path maps them (`d{i}` the drive, `m{i}` the readout, `u{k}` the coupler of
   `coupling_dict`), with a test of each kind of instruction.
2. **The guide** in the README, and the SDK's error for a pulse schedule points to it, as does
   the `OpenPulseBackend` deprecation; DESIGN.md describes both levels.

## Step 10: close out

1. Read `DESIGN.md` against the tree: every path it names exists.
2. Run `dev/e2e_native_test.sh` against the backend release that ships B2, B3 and B6, and check
   the plan's end state holds.
3. Delete `docs/prototypes/` and this file; the history keeps both.
