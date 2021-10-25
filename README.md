# Installation

## Package installation
* cd tergite-qiskit-connector
* pip install -e .
* (optional) create provider account configuration file $HOME/.qiskit/tergiterc


## Provider account configuration
The provider account configuration is stored at a file
  > $HOME/.qiskit/tergiterc
under section(s) [service <service name>].
It is possible to provide a configuration for multiple services.

Example:
--------

  > [service mss 1]
  > url = http://my_computer.mc2.chalmers.se:5000
  > token = None
  > verify = False
  >
  > [service mss 2]
  > url = http://my_computer.mc2.chalmers.se:5001
  > note = Secondary service on port 5001

Currently, only the field 'url' is obligatory. Other fields
are parsed and stored, but not used otherwise.


## Provider account usage
A specific provider account can be selected via:
  > provider = Tergite.get_provider('service name')
In the above example 'mss 1' is the service name.

Shall no service name be given, eg:
  > provider = Tergite.get_provider()
The first service found in tergiterc will be used.


## Creating a provide account on-fly
Shall the tergiterc file not provide any valid service section
a warning will be printed. A new provider account configuration can
be created on-fly with the following code:

  > from tergite.providers.tergite.provider_account import ProviderAccount
  > my_account = ProviderAccount("service name", "http://myaddress.com:port")
  > provider = Tergite.use_provider_account(my_account)

For later convenience, it is possible to save the newly created account in the
tergiterc file with "safe=True" option.

  > provider = Tergite.use_provider_account(my_account, save=True)


# Usage
See examples in the 'tests' folder.
