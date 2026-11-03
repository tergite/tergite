# Step 1 sign-off: tests, and the tooling to run them

A user acceptance test for step 1 of [REFACTOR.md](../../REFACTOR.md). It needs uv, MongoDB
(`mongod`, `mongosh`), git and curl, and checkouts of tergite-frontend and tergite-backend
beside this one. Until tergite-backend merges its three fixes (the branches
`fix/reconnect-clusters-after-recalibration`, `fix/simulators-partial-measurement` and
`fix/report-cancelled-jobs-to-mss`), check out a branch that has all three, such as
`sdk-refactor/e2e-combined`.

1. **The unit suite is fast and lint is clean.**

   ```bash
   uv sync && uv run pytest
   uv run black --check tergite tests dev && uv run isort --check-only tergite tests dev && uv run pyflakes tergite tests dev
   ```

   188 tests pass in under ten seconds, the style guide among them, and the linters find
   nothing.

2. **The e2e runs natively, in about two minutes.**

   ```bash
   FRONTEND_PATH=../tergite-frontend BACKEND_PATH=../tergite-backend ./dev/e2e_native_test.sh
   ```

   MongoDB, MSS and the backends start from the checkouts, with nothing in Docker, and 20
   tests pass in about 30 seconds. `DEBUG=True` keeps the services up; their logs are in
   `temp-native/logs/`.

3. **The performance checks compare with the baseline.**

   ```bash
   FRONTEND_PATH=../tergite-frontend BACKEND_PATH=../tergite-backend ./dev/perf/record.sh /tmp/perf
   uv run python dev/perf/compare.py dev/perf/baselines /tmp/perf
   ```

   Each measure prints beside its baseline, and `compare.py` exits 0. The baselines were
   recorded on one Mac; on another machine, record your own baseline first and compare with
   that.

4. **CI runs all three.** On a merge request, GitLab's `test` job lints and runs the unit
   suite with uv on Python 3.13, and its `e2e` job runs `dev/e2e_native_test.sh` against
   the frontend's and backend's branches of the same name, or `main`.
