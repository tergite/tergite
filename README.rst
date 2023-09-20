Tergite Qiskit Connector
========================

`Qiskit <https://github.com/Qiskit/qiskit>`_ provider for the Tergite quantum computers.

Installation
------------

Install using pip

.. code:: shell

    pip install tergite_qiskit_connector

Dependencies
------------

- `Python +3.8 <https://www.python.org/>`_
- `Qiskit <https://github.com/Qiskit/qiskit>`_

Getting Started
---------------

- Ensure you have `Python +3.8 <https://www.python.org/>`_ installed.
- Create an account with `Tergite <https://www.qal9000.se/>`_ if you haven't already.
- You should receive a set of credentials to access Tergite with.
- Create a ``main.py`` file and add the following code

.. code:: python

    import qiskit.circuit as circuit
    import qiskit.compiler as compiler
    from tergite_qiskit_connector.providers.tergite import Tergite
    from tergite_qiskit_connector.providers.tergite.provider_account import ProviderAccount

    if __name__ == "__main__":
        # the Tergite API URL e.g. "https://api.tergite.example"
        API_URL = "https://api.qal9000.se"
        # API token for connecting to tergite. Required if no username/password
        API_TOKEN = <your Tergite API key>
        # API username, required if API_TOKEN is not set
        API_USERNAME = "<your API username>"
        # API password, required if API_USERNAME is set
        API_PASSWORD = "<your API password>"
        # The name of the Quantum Computer to use from the available quantum computers
        BACKEND_NAME = "QC1"
        # the name of this service. For your own bookkeeping.
        SERVICE_NAME = "local"

        # create the Qiskit circuit
        qc = circuit.QuantumCircuit(2, 2)
        qc.h(1)
        qc.measure(1, 1)
        qc.draw()

        # create a provider
        account_extras = {}
        if API_USERNAME:
            account_extras = {
                "username": API_USERNAME,
                "password": API_PASSWORD
            }

        # provider account creation can be skipped in case you already saved
        # your provider account to the `~/.qiskit/tergiterc` file.
        # See below how that is done.
        account = ProviderAccount(
            service_name=SERVICE_NAME,
            url=API_URL,
            token=API_TOKEN,
            extras=account_extras
        )
        provider = Tergite.use_provider_account(account)
        # to save this account to the `~/.qiskit/tergiterc` file, add the `save=True`
        # provider = Tergite.use_provider_account(account, save=True)

        # Get the tergite backend in case you skipped provider account creation
        # provider = Tergite.get_provider(service_name=SERVICE_NAME)
        backend = chalmers.get_backend(BACKEND_NAME)
        backend.set_options(shots=1024)

        # compile the circuit
        tc = compiler.transpile(qc, backend=backend)
        tc.draw()

        # run the circuit
        job = backend.run(tc, meas_level = 2)

        # view the results
        job.results()

- Run the script

.. code:: shell

    python main.py

- Congratulations! You have run your first quantum circuit on a Tergite quantum computer.

ToDo
----

- [ ] Add Github actions, to push to pypi, and test code
- [ ] Add Github badges
- [ ] Add bitbucket pipeline to update production branch
  and push to github (downstream)
- [ ] Cleanup the code generally (downstream)
- [ ] Add docs and doc generation (downstream)

Contribution Guidelines
-----------------------

If you would like to contribute to tergite-qiskit-connector, please have a look at our
`contribution guidelines <./CONTRIBUTING.rst>`_

Authors
-------

The `contributors <./CONTRIBUTORS.rst>`_, to tergite-qiskit-connector are happy to
share this our work with you. For the License information, look at `License <#license>`_

ChangeLog
---------

To view the changelog for each version, have a look at
the `CHANGELOG.md <./CHANGELOG.md>`_ file.


License
-------

`Apache 2.0 License <./LICENSE.txt>`_
