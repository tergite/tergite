# Step 6 sign-off: accounts and the provider

A user acceptance test for step 6 of [REFACTOR.md](../../REFACTOR.md), with the setup of
[step 4's](04-circuits.md). Each Python snippet runs in `uv run python`, against the stack,
with `HOME` pointed at an empty folder so that the real `~/.qiskit/tergiterc` is untouched.

1. **Saved accounts keep their place and their characters.**

   ```python
   from tergite import Tergite
   Tergite.use_provider_account("e2e", url="http://127.0.0.1:8202", token="<APP_TOKEN>", save=True)
   Tergite.use_provider_account("other", url="http://example.com/a%20b", save=True)
   Tergite.use_provider_account("e2e", url="http://127.0.0.1:8202", token="<APP_TOKEN>", save=True)
   ```

   `~/.qiskit/tergiterc` holds `[service e2e]` then `[service other]`, with the `%20` as typed.
   Saving with a `%` used to fail, and saving `e2e` again used to move it below `other`.

2. **A misspelt service raises.** In a new shell, `Tergite.get_provider("e2")` raises
   `TergiteError: No provider account is named 'e2'; there are: e2e, other`, and
   `Tergite.get_provider()` returns the `e2e` provider. The misspelling used to return `e2e`
   silently, whatever the name.

3. **A device that comes online is seen.** With `provider = Tergite.get_provider("e2e")`,
   switch Loke off in MSS (insert it into `switched_off_devices`, as `dev/e2e_native_test.sh`
   removes it): `provider.get_backend("Loke").data.is_online` is `False`. Remove it again, and
   the same call, on the same provider, gives `True`; it used to keep the first answer.

4. **A recalibration reaches the target.** On `backend = provider.get_backend("Loke")`, read
   `backend.target`, then recalibrate Loke (e.g. restart its backend). The next `backend.run()`
   registers the job with the new `last_calibrated`, and `backend.target` is a new object;
   without a recalibration, it is the same object after a run.

5. **The performance checks hold.** `./dev/perf/record.sh /tmp/perf` and
   `compare.py dev/perf/baselines /tmp/perf` exit 0.
