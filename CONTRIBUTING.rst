Contributing to tergite-qiskit-connector
========================================

**This project is currently not accepting pull requests from the general public yet.**

**It is currently being developed by the core developers only.**

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

Versioning
----------

When versioning we follow the format ``{year}.{month}.{patch_number}`` e.g. ``2023.12.0``.

We Develop with Github
----------------------

We use Github to host code, to track issues and feature requests, as well as accept pull requests.

But We Use `Github Flow <https://docs.github.com/en/get-started/quickstart/github-flow>`_,
So All Code Changes Happen Through Pull Requests

Pull requests are the best way to propose changes to the codebase (we
use `Github Flow <https://docs.github.com/en/get-started/quickstart/github-flow>`_). We actively welcome your pull
requests:

1. Clone the repo and create your branch from ``main``.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

Any contributions you make will be under the Apache 2.0 Software Licenses
-------------------------------------------------------------------------

In short, when you submit code changes, your submissions are understood to be under the
same `Apache 2.0 License <./LICENSE.txt>`_ that covers the project. Feel free to contact the maintainers if that's a concern.

Report bugs using Github's `issues <https://github.com/tergite/tergite-qiskit-connector/issues>`
--------------------------------------------------------------------------------------------------

We use Github issues to track bugs. Report a bug
by `opening a new issue <https://github.com/tergite/tergite-qiskit-connector/issues>`_; it's that easy!

## Write bug reports with detail, background, and sample code

`This is an example <http://stackoverflow.com/q/12488905/180626>`_.
Here's `another example from Craig Hockenberry <http://www.openradar.me/11905408>`_.

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  * Be specific!
  * Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

..
    Use a Consistent Coding Style
    -----------------------------

    * Use `black <https://pypi.org/project/black/>`_

License
-------

By contributing, you agree that your contributions will be licensed under its Apache 2.0 License.

How to Test
-----------

- Make sure you have `python <https://www.python.org/>`_ installed.
- Make sure you have `poetry <https://python-poetry.org/>`_ installed.
- Clone the repo and enter its root folder

  .. code:: shell

    git clone git@github.com:tergite/tergite-qiskit-connector.git
    cd tergite-qiskit-connector

- Install the dependencies

  .. code:: shell

    poetry install

- Activate the environment

  .. code:: shell

    source $(poetry env info --path)/bin/activate

- Run the tests command

  .. code:: shell

    pytest tests


References
----------

This document was adapted from `a gist by Brian A. Danielak <https://gist.github.com/briandk/3d2e8b3ec8daf5a27a62>`_ which
was originally adapted from the open-source contribution guidelines
for `Facebook's Draft <https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md>`_
