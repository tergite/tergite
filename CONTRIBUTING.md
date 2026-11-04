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

## Versioning

When versioning we follow the format `{year}.{month}.{patch_number}` e.g. `2023.12.0`.

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

## References

This document was adapted from [a gist by Brian A. Danielak](https://gist.github.com/briandk/3d2e8b3ec8daf5a27a62) which was originally adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md)
