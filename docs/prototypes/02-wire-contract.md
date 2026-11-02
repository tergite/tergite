# Step 2 sign-off: the wire contract, from OpenAPI

A user acceptance test for step 2 of [REFACTOR.md](../../REFACTOR.md), with the same setup
as [step 1's](01-tests-and-tooling.md). tergite-backend's checkout needs its committed spec
(`feature/commit-openapi-spec`, merged into `sdk-refactor/e2e-combined`).

1. **The models are what the specs generate.**

   ```bash
   uv run python -m dev.openapi.generate && git status --short tergite/api
   uv run pytest tests/test_openapi.py
   ```

   Generating changes nothing, and the test passes.

2. **A spec that moves fails the test.** Change a description in `dev/openapi/mss.json`,
   e.g. that of `Device`, and run `uv run pytest tests/test_openapi.py`: it fails, saying
   `mss_models.py is stale`. Undo the change.

3. **Syncing takes the services' specs.**

   ```bash
   FRONTEND_PATH=../tergite-frontend BACKEND_PATH=../tergite-backend ./dev/openapi/sync.sh
   git status --short dev/openapi tergite/api
   ```

   Against checkouts at the versions the SDK targets, nothing changes.

4. **The e2e checks what the services serve.** `./dev/e2e_native_test.sh` prints
   `Checking that MSS and the backend serve the schemas dev/openapi pins` and goes on to its
   20 tests. Against a backend or MSS whose DTOs differ from the pinned copies, it stops
   there, naming the schemas that differ.

5. **The performance checks hold.** `./dev/perf/record.sh /tmp/perf client` and
   `uv run python dev/perf/compare.py dev/perf/baselines /tmp/perf` exit 0.
