# Tergite

[![PyPI version](https://badge.fury.io/py/tergite.svg)](https://pypi.python.org/pypi/tergite/) [![license](https://img.shields.io/pypi/l/tergite.svg)](https://pypi.python.org/pypi/tergite/) [![CI](https://github.com/tergite/tergite/actions/workflows/ci.yml/badge.svg)](https://github.com/tergite/tergite/actions) [![PyPI pyversions](https://img.shields.io/pypi/pyversions/tergite.svg)](https://pypi.python.org/pypi/tergite/)  

The SDK in the [Tergite software stack](https://tergite.github.io/): a [Qiskit](https://github.com/Qiskit/qiskit)
provider for running circuits and pulses on the Swedish quantum computer.

**This project is developed by a core group of collaborators.**
**Chalmers Next Labs AB (CNL) takes on the role of managing and maintaining this project.**

## Version Control

The tergite stack is developed on a separate version control system and mirrored on Github.
If you are reading this on GitHub, then you are looking at a mirror: its pull requests and issues
are not read. Please get in touch via email <contact.quantum@chalmersnextlabs.se> instead.

## Installation

```shell
pip install tergite
```

For pulse-level jobs written with [oqpy](https://github.com/openqasm/oqpy), install the `pulse` extra:

```shell
pip install 'tergite[pulse]'
```

## Dependencies

- [Python 3.13+](https://www.python.org/)
- [Qiskit 2.1+](https://github.com/Qiskit/qiskit)
- [Tergite Frontend](https://github.com/tergite/tergite-frontend), and a
  [Tergite Backend](https://github.com/tergite/tergite-backend) that runs circuits

## Quick Start

- Get an API token: create an account with [QAL 9000](https://www.qal9000.se/), or run your own
  [Tergite Frontend](https://github.com/tergite/tergite-frontend), and make an app token in its dashboard.

- Connect, and pick a backend

```python
from tergite import Tergite

provider = Tergite.use_provider_account(
    service_name="MY_SERVICE_NAME",
    url="https://api.qal9000.se",  # or the URL of your own Tergite API
    token="MY_API_TOKEN",
)
print(provider.backends())
backend = provider.get_backend("Loke")
```

- Run a circuit, transpiled to that backend

```python
from qiskit import QuantumCircuit, transpile

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

job = backend.run(transpile(qc, backend), shots=1000)
job.wait_for_final_state()
print(job.result().get_counts())
```

To keep your account for later, pass `save=True`: see [docs/accounts.md](./docs/accounts.md).

## Documentation

| Document | Read it to |
| --- | --- |
| [docs/accounts.md](./docs/accounts.md) | save an account, take it from the environment, or use the SDK on a shared computer |
| [docs/running_circuits.md](./docs/running_circuits.md) | run circuits and set shots and measurement levels |
| [docs/pulses.md](./docs/pulses.md) | run pulse-level jobs, and migrate from Qiskit pulse schedules |
| [examples/](./examples) | see notebooks and scripts that use the SDK |
| [DESIGN.md](./DESIGN.md) | understand how the SDK is built, before changing it |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | run the tests and follow the code conventions |

## Contribution Guidelines

If you would like to contribute to tergite, please have a look at our [contribution guidelines](./CONTRIBUTING.md)

## Authors

This project is a work of [many contributors](https://github.com/tergite/tergite/graphs/contributors).

Special credit goes to the authors of this project as seen in the [CREDITS](./CREDITS.md) file.

## ChangeLog

To view the changelog for each version, have a look at the [CHANGELOG.md](./CHANGELOG.md) file.

## License

[Apache 2.0 License](./LICENSE.txt)

## Acknowledgements

This project was sponsored by:

- [Knut and Alice Wallenberg Foundation](https://kaw.wallenberg.org/en) under the [Wallenberg Center for Quantum Technology (WACQT)](https://www.chalmers.se/en/centres/wacqt/) project at [Chalmers University of Technology](https://www.chalmers.se)
- [Nordic e-Infrastructure Collaboration (NeIC)](https://neic.no) and [NordForsk](https://www.nordforsk.org/sv) under the [NordIQuEst](https://neic.no/nordiquest/) project
- [European Union's Horizon Europe](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en) under the [OpenSuperQ](https://cordis.europa.eu/project/id/820363) project
- [European Union's Horizon Europe](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en) under the [OpenSuperQPlus](https://opensuperqplus.eu/) project
