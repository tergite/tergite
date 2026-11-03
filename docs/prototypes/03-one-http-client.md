# Step 3 sign-off: one HTTP client

A user acceptance test for step 3 of [REFACTOR.md](../../REFACTOR.md), with the same setup
as [step 1's](01-tests-and-tooling.md).

1. **requests is gone.** `uv tree --package tergite | grep -c requests` finds it only where
   another package brings it, if at all, and `grep -rn "import requests" tergite` finds
   nothing.

2. **Errors say what failed, and old `except` clauses still catch them.** Against the e2e
   stack (`DEBUG=True ./dev/e2e_native_test.sh`, then a Python shell):

   ```python
   from tergite import Tergite
   from tergite.exc import ApiError, BackendNotFoundError

   provider = Tergite.use_provider_account("bad", url="http://127.0.0.1:8202", token="nope")
   backend = provider.get_backend("qiskit_pulse_1q")
   try:
       provider.get_backend("no-such-device")
   except BackendNotFoundError as exp:
       print("not found:", exp)
   ```

   It prints `not found: 'No backend matches the criteria'`. Running a circuit on
   `backend` raises `ApiError: unable to register job at the remote API: …` with
   `status_code` 401, which `except RuntimeError` catches too.

3. **A token changed on the account is used.** Set `provider.account.token` to the e2e's
   `APP_TOKEN` and run the circuit again: it is accepted.

4. **The e2e and the performance checks hold.** `./dev/e2e_native_test.sh` passes its 20
   tests, and `./dev/perf/record.sh /tmp/perf client` with `compare.py` exits 0.
