# Tergite

[![PyPI version](https://badge.fury.io/py/tergite.svg)](https://pypi.python.org/pypi/tergite/) [![license](https://img.shields.io/pypi/l/tergite.svg)](https://pypi.python.org/pypi/tergite/) [![CI](https://github.com/tergite/tergite/actions/workflows/ci.yml/badge.svg)](https://github.com/tergite/tergite/actions) [![PyPI pyversions](https://img.shields.io/pypi/pyversions/tergite.svg)](https://pypi.python.org/pypi/tergite/)  

The SDK in the [Tergite software stack](https://tergite.github.io/) for connecting to the Swedish quantum computer.    

It includes:

- [Qiskit](https://github.com/Qiskit/qiskit) providers

**This project is developed by a core group of collaborators.**
**Chalmers Next Labs AB (CNL) takes on the role of managing and maintaining this project.**

## Version Control

The tergite stack is developed on a separate version control system and mirrored on Github.
If you are reading this on GitHub, then you are looking at a mirror.

## Installation

Install using pip

```shell
pip install tergite
```

## Dependencies

- [Python 3.9, 3.10](https://www.python.org/)
- [Qiskit +v1.0](https://github.com/Qiskit/qiskit)
- [Tergite Frontend](https://github.com/tergite/tergite-frontend)

## Provider Setup

- Ensure you have [Python +3.9](https://www.python.org/) installed.

- Create an account with [QAL 9000](https://www.qal9000.se/) if you haven't already. (Or you can have your own [tergite Frontend](https://github.com/tergite/tergite-frontend) running)

- With the credentials received from Tergite, create and save a provider account by calling `Tergite.use_provider_account(account, save=True)`.

```python
from tergite.qiskit.providers import Tergite
from tergite.qiskit.providers.provider_account import ProviderAccount

TERGITE_API_URL="https://api.qal9000.se"  # or the URL to your own tergite MSS

account = ProviderAccount(
      service_name="MY_SERVICE_NAME", url="TERGITE_API_URL", token="MY_API_TOKEN"
)
provider = Tergite.use_provider_account(account, save=True)
```

The code above stores your credentials in a configuration file called `tergiterc`, located in `$HOME/.qiskit` folder, `$HOME` being your home directory.

Once saved, you can retrieve this particular account using the `SERVICE_NAME` from anywhere in your code. From the provider, you can retrieve any backend you wish by name.

```python
provider = Tergite.get_provider(service_name="MY_SERVICE_NAME")

# display list of backends
print(provider.backends())

# access the 'Loke' backend
backend = provider.get_backend("Loke")
```

### Create a Throw-away Provider Account

- Alternatively, you can create a provider account that won't be saved. This is useful in things like automated tests. Just call the `Tergite.use_provider_account(account)` without the `save` option.

```python
# the account from before
provider = Tergite.use_provider_account(account)
```

- You can look at the [examples folder](./examples) for more samples.

## Examples and demos

This project has a long history with contributions of many different partners. 
All files in the `archive` folder are scripts from live demonstrations, which show the historical progression of the project.
Since research in quantum computing is moving fast, these files are meant to inspire and might not be functional with the source code of this library.

To find out how to use the library, please take a look into the notebooks and scripts inside the `examples` folder.

## ToDo

- [ ] Add docs and doc generation

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
