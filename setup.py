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

#with open("requirements.txt", mode="r") as _f:
#    REQUIREMENTS = _f.readlines()

REQUIREMENTS = [
    "requests>=2.25.1",
    "python_dateutil>=2.8.1",
    "python-multipart>=0.0.5",
    "qiskit-terra==0.22.0",
    "pandas>=1.4.2",
    "tqdm>=4.64.1",
    "qiskit-aer>=0.11.0",
    "qiskit-experiments>=0.4.0",
    "qiskit-ibmq-provider>=0.19.2",
    "qiskit-ignis>=0.7.1",
    "more-itertools>=8.14.0",
    "matplotlib>=3.5.3",
    "matplotlib-inline>=0.1.6"
]

setup(
    name="tergite-qiskit-connector",
    author_emails="dobsicek@chalmers.se",
    license="Apache 2.0",
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    python_requires=">=3.8",
)
