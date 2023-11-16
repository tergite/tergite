# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

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