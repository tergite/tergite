# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project follows versions of format `{year}.{month}.{patch_number}`.

## [Unreleased]

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