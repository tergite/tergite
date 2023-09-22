Tergite Qiskit Connector
========================

|PyPI version| |license| |CI| |PyPI pyversions|

The `Qiskit <https://github.com/Qiskit/qiskit>`_ provider for connecting to the Tergite quantum computers.

Installation
------------

Install using pip

.. code:: shell

    pip install tergite_qiskit_connector

Dependencies
------------

- `Python +3.8 <https://www.python.org/>`_
- `Qiskit <https://github.com/Qiskit/qiskit>`_

Provider Setup
---------------

- Ensure you have `Python +3.8 <https://www.python.org/>`_ installed.
- Create an account with `Tergite <https://www.qal9000.se/>`_ if you haven't already.
- With the credentials received from Tergite, create and save a provider account by calling
  ``Tergite.use_provider_account(account, save=True)``.

  When using "API_TOKEN", use:

  .. code:: python

    from tergite_qiskit_connector.providers.tergite.provider_account import ProviderAccount

    account = ProviderAccount(
        service_name="MY_SERVICE_NAME", url="TERGITE_API_URL", token="MY_API_TOKEN", extras={}
    )
    provider = Tergite.use_provider_account(account, save=True)

  When using "USERNAME" and "PASSWORD", use:

  .. code:: python

    from tergite_qiskit_connector.providers.tergite.provider_account import ProviderAccount

    account = ProviderAccount(
            service_name="MY_SERVICE_NAME",
            url="TERGITE_API_URL",
            extras={
                "username": "MY_TERGITE_API_USERNAME",
                "password": "MY_TERGITE_API__PASSWORD"
            }
    )
    provider = Tergite.use_provider_account(account, save=True)

  The code above stores your credentials in a configuration file called ``tergiterc``, located in ``$HOME/.qiskit``
  folder, ``$HOME`` being your home directory.

  Once saved, you can retrieve this particular account using the ``SERVICE_NAME`` from anywhere in your code.
  From the provider, you can retrieve any backend you wish by name.

  .. code:: python

    provider = Tergite.get_provider(service_name="MY_SERVICE_NAME")

    # display list of backends
    print(provider.backends())

    # access the 'Loke' backend
    backend = provider.get_backend("Loke")


Create a Throw-away Provider Account
************************************

- Alternatively, you can create a provider account that won't be saved. This is useful in things like automated tests.
  Just call the ``Tergite.use_provider_account(account)`` without the ``save`` option.

  .. code:: python

    # the account from before
    provider = Tergite.use_provider_account(account)

- You can look at the `examples folder <./examples>`_ for more samples.

ToDo
----

- [ ] Cleanup the code generally
- [ ] Add docs and doc generation

Contribution Guidelines
-----------------------

If you would like to contribute to tergite-qiskit-connector, please have a look at our
`contribution guidelines <./CONTRIBUTING.rst>`_

Authors
-------

This project is a work of
`many contributors <https://github.com/tergite/tergite-qiskit-connector/graphs/contributors>`_.

Special credit goes to the authors of this project as seen in the `CREDITS <./CREDITS.rst>`_ file.

ChangeLog
---------

To view the changelog for each version, have a look at
the `CHANGELOG.md <./CHANGELOG.md>`_ file.


License
-------

`Apache 2.0 License <./LICENSE.txt>`_


.. |PyPI version| image:: https://badge.fury.io/py/tergite-qiskit-connector.svg
   :target: https://pypi.python.org/pypi/tergite-qiskit-connector/

.. |license| image:: https://img.shields.io/pypi/l/tergite-qiskit-connector.svg
   :target: https://pypi.python.org/pypi/tergite-qiskit-connector/

.. |CI| image:: https://github.com/tergite/tergite-qiskit-connector/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/tergite/tergite-qiskit-connector/actions

.. |PyPI pyversions| image:: https://img.shields.io/pypi/pyversions/tergite-qiskit-connector.svg
   :target: https://pypi.python.org/pypi/tergite-qiskit-connector/