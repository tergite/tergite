# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2021
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


from setuptools import find_packages, setup

with open("requirements.txt", mode="r") as _f:
    REQUIREMENTS = _f.readlines()

setup(
    name="tergite-qiskit-connector",
    author_emails="dobsicek@chalmers.se",
    license="Apache 2.0",
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    python_requires=">=3.8",
)
