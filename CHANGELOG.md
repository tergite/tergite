# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project follows versions of format `{year}.{month}.{patch_number}`.

## [Unreleased]

## [2025.09.0] - 2025-10-02

### Added

- Add e2e tests for meas_level 1 with clustering algorithm populaton and distance 

### Changed

- Extend data type of the job results to allow IQpoints together with HexMap for meas_level 1
- Clean up classical register of quantum circuits before scheduling them to remove idle classical registers
- Changed to use the `access_token` got on job submission to MSS, to submit/cancel jobs to BCC as well as download logfiles.

## [2025.06.1] - 2025-06-17

### Changed

- Removed unwanted artefacts from the packaged library

### Fixed

- Make folder removal in e2e fault tolerant

## [2025.06.0] - 2025-06-16

### Added

- Implemented job cancellation

### Changed

- BREAKING: Changed the MSS endpoints `/v2/devices` to `/devices`
- BREAKING: Changed the MSS endpoints `/v2/calibrations` to `/calibrations`
- BREAKING: Changed the expected Device info schema to include 'number_of_resonators' and 'number_of_couplers'
- Added pydantic as an explicit dependency
- Moved completely from dataclasses to pydantic models
- Set the minimum permitted python to 3.12
- Removed the `tergite.qiskit` package and moved everything to the `tergite` package
- Removed the `tergite.qiskit.providers` package and moved everything to the parent package
- Raise `QiskitBackendNotFoundError` when malformed backend is returned in data instead of `TypeError`
- BREAKING: Remove `extras` from `AccountInfo`
- BREAKING: Change signature of `Tergite.use_provider_account(account, save)` to `Tergite.use_provider_account(service_name, url, token, save)`

## [2025.03.1] - 2025-03-18

### Changed

- Changed the backend configurations for the full e2e to run with the new backend configuration files

## [2025.03.0] - 2025-03-14

### Changed

- Refactor: Changed a few error messages to include the original error
- Refactor: Changed the Job metadata to always be generated on the backend.  
  It was originally setting them both on the backend and the SDK.
- Upgraded to Poetry > 2.1

### Added

- Added caching of calibration requests to reduce number of calls to remote API
- Added caching on Job's `status()`, `result()`, `download_url` to reduce number of calls to remote API
- Added sending of `calibration_date` (str) query parameter during job registration.
- Added end-to-end tests for `qiskit_pulse_1q` simulator backend
- Added end-to-end tests for `qiskit_pulse_2q` simulator backend
- Added Gitlab and Github CI configurations for end-to-end tests

## [2024.12.1] - 2024-12-18

### Changed

- Updated tests to run tests against multiple backends
- Updated `Provider.job()` to return a `Job` instance without an upload_url

### Fixed

- Fixed the error 'Coupling (0, 0) not a coupling map' for backends without couplers

## [2024.12.0] - 2024-12-13

### Added

- Added the `job()` method to provider to retrieve job by job ID
- Added functionality to get control channel index given qubit tuple
- Added two qubit CZ gate functionality 

### Changed

- Upgraded Qiskit version to 1.0+, <1.3
- Use MSS v2 endpoints for backend and calibration data

## [2024.09.1] - 2024-09-26

## Fixed

- Limited to qiskit == 0.39.0 to avoid unexpected errors with packages that depend on qiskit

## [2024.09.0] - 2024-09-16

- Nothing changed

## [2024.04.1] - 2024-05-29

### Added

### Changed

- Changed README.rst to README.md
- Changed CONTRIBUTING.rst to CONTRIBUTING.md
- Changed CREDITS.rst to CREDITS.md
- Updated the contribution guidelines and government model statements

### Fixed

## [2024.04.0] - 2024-04-19

### Added

### Changed

- Renamed tergite-qiskit-connector to `tergite`

### Fixed

## [2024.02.0] - 2024-03-14

This is part of the tergite release v2024.02.0 which introduces authentication, authorization and accounting to the
tergite stack

### Added

### Changed

### Fixed

### Contributors

-   Martin Ahindura <martin.ahindura@chalmers.se>

## [2023.12.0] - 2024-03-04

This is part of the tergite release v2023.12.0 that is the last to support [Labber](https://www.keysight.com/us/en/products/software/application-sw/labber-software.html).
Labber is being deprecated.

### Added

### Changed

- The format of the version to `{year}.{month}.{patch_number}`

### Fixed

### Contributors

-   Martin Ahindura <martin.ahindura@chalmers.se>

## [0.2.1] - 2024-02-21

### Added

### Changed

### Fixed

- Fixed 'TypeError: 'NoneType' object is not iterable' in use_provider_account(account, save=True)
- Fixed 'ProviderAccount.__init__() got an unexpected keyword argument' when loading accounts from tergiterc file

## [0.2.0] - 2024-02-15

### Added

### Changed

- Removed username-password authentication

### Fixed

## [0.1.2] - 2024-02-15

### Added

### Changed

- Changed the examples in the examples folder to experiments that work

### Fixed

## [0.1.1] - 2024-02-14

### Added

- Reintroduced the archives of past projects

### Changed

### Fixed

- Fixed wrong backend attached to jobs created in MSS

## [0.1.0] - 2023-11-16

### Added

### Changed

### Fixed

- Fixed typo of `pulse_amptitude` of `readout_resonator` in `template_schedules.py`
  - This is a breaking change that makes versions before 0.1.0 fail with our current backends

## [0.0.2] - 2023-10-02

### Added

- Added automated tests
- Added examples folder with notebooks and python scripts

### Changed

### Fixed

- Fixed `backend.run()` when backend has basic auth
- Fixed `backend.run()` when backend has bearer auth
- Fixed `job.result()` when backend has basic auth
- Fixed `job.result()` when backend has bearer auth
- Fixed `job.status()` when backend has basic auth
- Fixed `job.status()` when backend has bearer auth
- Fixed `job.download_url` when backend has basic auth
- Fixed `job.download_url` when backend has bearer auth

## [0.0.1] - 2023-09-20

### Added

- Initial release

### Changed

### Fixed