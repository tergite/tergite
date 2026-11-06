# Contributing to tergite

**This project is currently not accepting pull requests from the general public yet.**

**It is currently being developed by the core developers only.**

We love your input! We want to make contributing to this project as easy
and transparent as possible, whether it's:

-   Reporting a bug
-   Discussing the current state of the code
-   Submitting a fix
-   Proposing new features
-   Becoming a maintainer

## Government Model

[Chalmers Next Labs AB (CNL)](https://chalmersnextlabs.se) manages and maintains this project on behalf of all contributors.

## Version Control

Tergite is developed on a separate version control system and mirrored on Github.
If you are reading this on GitHub, then you are looking at a mirror.

## Contacting the Tergite Developers

Since the Github repositories are only mirrors, no Github pull requests or Github issue/bug reports
are looked. Please get in touch via email <contact.quantum@chalmersnextlabs.se> instead.

Take note that the maintainers may not answer every email.

## But We Use [Github Flow](https://docs.github.com/en/get-started/quickstart/github-flow), So All Code Changes Happen Through Pull Requests

Pull requests are the best way to propose changes to the codebase (we
use [Github Flow](https://docs.github.com/en/get-started/quickstart/github-flow)). We actively welcome your pull
requests:

1. Clone the repo and create your branch from `main`. Read [DESIGN.md](./DESIGN.md) first: it has
   the SDK's architecture and the conventions code is held to.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Any contributions you make will be under the Apache 2.0 Software Licenses

In short, when you submit code changes, your submissions are understood to be under the
same [Apache 2.0 License](./LICENSE.txt) that covers the project. Feel free to contact the maintainers if that's a concern.

## Write bug reports with detail, background, and sample code

[This is an example](http://stackoverflow.com/q/12488905/180626).
Here's [another example from Craig Hockenberry](http://www.openradar.me/11905408).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People _love_ thorough bug reports. I'm not even kidding.

## License

By contributing, you agree that your contributions will be licensed under its Apache 2.0 License.

## Contributor Licensing Agreement

Before you can submit any code, all contributors must sign a
contributor license agreement (CLA). By signing a CLA, you're attesting
that you are the author of the contribution, and that you're freely
contributing it under the terms of the Apache-2.0 license.

The [individual CLA](https://tergite.github.io/contributing/icla.pdf) document is available for review as a PDF.

Please note that if your contribution is part of your employment or
your contribution is the property of your employer,
you will also most likely need to sign a [corporate CLA](https://tergite.github.io/contributing/ccla.pdf).

All signed CLAs are emails to us at <contact.quantum@chalmersnextlabs.se>.

## How to Test

-   Install [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs
    Python 3.13 for you if you do not have it.

-   Clone the repo and enter its root folder

``` shell
git clone git@github.com:tergite/tergite.git
cd tergite
```

-   Install the dependencies, into `.venv`

``` shell
uv sync
```

-   Run the tests, then the linters CI runs

``` shell
uv run pytest
```

``` shell
uv run ruff format --check && uv run ruff check
```

-   Run the example notebooks, with Jupyter alongside

``` shell
uv run --with jupyter jupyter lab examples/notebooks
```

## How to Run End-to-end Tests

`dev/e2e_native_test.sh` runs `tests/e2e` against MSS and the backends, all running natively
from checkouts of [tergite-frontend](https://github.com/tergite/tergite-frontend) and
[tergite-backend](https://github.com/tergite/tergite-backend), with fresh data in
`temp-native/`.

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/), MongoDB (`mongod` and
  `mongosh`), git and curl.
- Ensure nothing is running on ports 8201, 8202, 8203 and 27218.
- Run it against local checkouts, or clones of the given repositories and branches:

``` shell
FRONTEND_PATH="../tergite-frontend" BACKEND_PATH="../tergite-backend" ./dev/e2e_native_test.sh
```

``` shell
FRONTEND_REPO="https://github.com/tergite/tergite-frontend.git" \
  BACKEND_REPO="https://github.com/tergite/tergite-backend.git" \
  ./dev/e2e_native_test.sh
```

Its arguments go to pytest, e.g. `./dev/e2e_native_test.sh -k quantify`. Set `DEBUG=True` to
keep the services running afterwards; their logs are in `temp-native/logs/`.

## How to Check Performance

`dev/perf/record.sh` records the client's benchmarks against mocked services, and the round trip
of jobs against the end-to-end stack, which it starts as above; `compare.py` fails on a measure
more than 10% and its noise floor worse than the baselines in `dev/perf/baselines`, or on one more
HTTP call.

``` shell
FRONTEND_PATH="../tergite-frontend" BACKEND_PATH="../tergite-backend" ./dev/perf/record.sh /tmp/perf
```

``` shell
uv run python dev/perf/compare.py dev/perf/baselines /tmp/perf
```

The numbers are the machine's own, so compare runs made on one machine. `./dev/perf/record.sh
/tmp/perf client` records the client's alone, without the stack.

## Where the Tests Are

| Level | Where | Mocks |
| --- | --- | --- |
| Unit and integration | `tests/`, `tests/integration/` | MSS and a BCC, mocked with respx from the JSON in `tests/fixtures/` |
| End-to-end | `tests/e2e/`, collected only with `IS_END_TO_END=true` | none: real MSS and backends, as above |
| Performance | `dev/perf/` | the client against mocks, and the round trip against the e2e stack |

- respx routes match in the order they are added, and the same pattern is the same route. A
  test changes an answer by re-routing that pattern, or by monkeypatching the fixture data a
  handler reads.
- Shared helpers and fixtures live in `tests/utils/`, one file per kind of helper.
- Pytest turns a `DeprecationWarning` into an error.
- `tests/test_styleguide.py` checks what ruff cannot: names, file layout, banner comments,
  licence headers, type hints and `__all__`. `tests/fixtures/styleguide_baseline.txt` lists
  code that broke the rules when the test was added. It only shrinks: a fix deletes its line.
- The e2e stack runs MongoDB, MSS and the backends natively from checkouts, with fresh data in
  `temp-native/`: `sim_1q` and `sim_2q` from tergite-backend's fixtures, and Loke, a dummy
  two-qubit device, from this repo's configs.

### Before a Merge Request

- `uv run ruff format --check`, `uv run ruff check` and `uv run pytest`;
- for a change to how the SDK talks to MSS or BCC, `dev/e2e_native_test.sh`;
- for a change that may cost time or memory, `dev/perf/record.sh` and `compare.py`. A change
  that moves a measure on purpose records new baselines in the same commit, saying why.

CI runs ruff and pytest on merge requests and `v*` tags, and the e2e on merge requests, `main`
and `v*` tags. The e2e checks out tergite-frontend and tergite-backend at the branch or tag of
the same name, else their newest release of the same month, else `main`. A `v*` tag publishes
to Test PyPI and PyPI, where `SHOULD_PUBLISH_TO_STAGING` or `SHOULD_PUBLISH_TO_PROD` is set.

## Where to Start

| Task | Where |
| --- | --- |
| A call to MSS or BCC | a method of `MssClient` or `BccClient` in `tergite/clients/`; a respx route in `tests/integration/conftest.py` |
| A field MSS or BCC sends | `dev/openapi/sync.sh` against their checkouts, then `uv run python -m dev.openapi.generate`; the diff to the pinned spec is the review |
| A gate the transpiler may use | `tergite/backends/target.py`; a case in `tests/test_target.py` |
| A public name | `tergite/__init__.py` and its `__all__`; its signature in `tests/integration/test_public_api.py` |
| An error a user catches | a subclass of `TergiteError` in `tergite/exc.py` |
| A test against the real stack | `tests/e2e/` |

Read [DESIGN.md](./DESIGN.md) first for how the code is laid out.

## Conventions

### Code Structure

Code reads like an article: the overview first, the detail below it. New code follows these
rules, and code a change touches is brought in line with them.

1. **A public function is a short list of calls**, each to a function named for the one thing
   it does. Don't extract one-liners, and don't split performance-critical paths.
2. **Callees sit below their callers.** A file runs: constants, public functions in the order
   a caller uses them, then private helpers in the order they are first called.
3. **A comment that labels a phase is a missing function**, named for what the phase does.
4. **Data is a struct; state gets a class.** Data is a pydantic model, a frozen `@dataclass`,
   an `Enum` or an `Exception`, with only derived views and `from_*`/`to_*` conversions. What
   owns state across calls (the HTTP clients, a backend's target, a job's status) is a class.
   Qiskit's base classes are the only inheritance: `TergiteBackend(BackendV2)` and
   `Job(JobV1)` are what users program against.
5. **Stateless behaviour is a module-level function** with explicit arguments, such as
   `get_target` and `get_result`. No `Protocol` or ABC with one implementation.
6. **Dependencies arrive as arguments.** Importing `tergite` does no I/O and prints nothing.
   Only `providers/accounts.py` reads the rc file, and only when asked to.
7. **One home per kind of thing.** HTTP in `tergite/clients/`, one package per service. Errors
   subclass `tergite.exc.TergiteError`. The public surface is `tergite/__init__.py`. Dev and
   test tooling lives in `dev/`.
8. **Prefer a reputable library, and vendor nothing.** When Qiskit removes something, the SDK
   stops needing it rather than copying it. The commit that adds our own code says why.
9. **Obvious beats clever.** Plain `if`/`else` over loops over tuples of fields. A value that
   is only defined stays where it is used.
10. **The wire is generated, not transcribed**, so a change on either side fails a test here,
    not a user's job.
11. **The public API holds.** `Tergite.use_provider_account`, `Tergite.get_provider`,
    `provider.backends`, `provider.get_backend`, `provider.job`, `backend.run`,
    `backend.target`, `backend.set_options`, `job.status`, `job.result`, `job.cancel`,
    `job.download_url` and `job.logfile` keep their signatures. A break needs a `Changed`
    changelog entry and, where possible, a deprecation warning for one release.

### Style

- **`ruff format` and `ruff check` are authoritative**; CI fails on any finding.
- **Names**: variables are nouns, functions are verbs, booleans start with `is_` or
  `should_`. No `build_*`: a constructed thing is a class, anything else is got, so `get_*`.
- **Constants at the top** of the file, after the imports.
- **Type hints everywhere**, return types included. What crosses a module is a model, never a
  bare dict.
- **Docstrings** say what a function does for its caller: one line where one line does,
  Google style (`Args:`, `Returns:`, `Raises:`) where it takes several arguments or raises
  what its caller handles.
- **Comments earn their place**: the constraint, the gotcha, the *why*. Never a restatement of
  the code or the history of a fix.
- **No banner comments.** A group that needs a label needs a docstring or its own file.
- **Tests**: the name says what it tests.
- **Licence header** on every file, with a line per contributing party.

### Commits and Changelog

- One logical change per commit.
- Every change users notice gets a [CHANGELOG.md](./CHANGELOG.md) entry under
  `[Unreleased]`, in `Added`/`Changed`/`Fixed`: one or two sentences on what changed and what a
  user would have hit before. The reasoning goes in the commit body.

### Releases

Versions are `{year}.{month}.{patch}`, e.g. `2026.06.0`, released with the rest of the stack.
A release candidate is `{version}-rc.{n}`. A release sets `version` in `pyproject.toml`, runs
`uv lock`, dates the `[Unreleased]` section of the changelog, and is tagged, signed, as
`v{version}`.

## References

This document was adapted from [a gist by Brian A. Danielak](https://gist.github.com/briandk/3d2e8b3ec8daf5a27a62) which was originally adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md)
