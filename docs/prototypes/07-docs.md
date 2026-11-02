# Step 7 sign-off: docs

A user acceptance test for step 7 of [REFACTOR.md](../../REFACTOR.md), with the setup of
[step 4's](04-circuits.md).

1. **DESIGN.md is the map.** [DESIGN.md](../../DESIGN.md) says what the SDK is, the calls a job
   makes to MSS and BCC, the job file and the memory, the package layout, how the wire models
   are regenerated and checked, the tests, CI and releases, and the conventions REFACTOR.md
   set. Each path and command in it exists and runs as written.

2. **The README runs.** Against the stack, with the account of its "Provider Setup" section
   pointed at `http://127.0.0.1:8202` and the e2e's app token, the code of "Running Circuits"
   prints counts of 1000 shots on `qiskit_pulse_2q`; an untranspiled `qc` with an `h` raises
   `TergiteError … transpile the circuit … first`.

3. **The examples run.** `./dev/e2e_native_test.sh` passes 21 tests, `test_hello_world_script`
   among them. Each notebook in `examples/notebooks`, with `API_URL` and `API_TOKEN` set to the
   stack's, runs to counts of 1024 shots; the two-qubit one's are mostly `00` and `11`.

4. **CONTRIBUTING is current.** Its contact address is tergite-frontend's,
   <contact.quantum@chalmersnextlabs.se>; its test, lint, e2e and performance commands run as
   written.

5. **Performance is unchanged.** No file in `tergite/` changed in this step, so step 6's
   records stand.
