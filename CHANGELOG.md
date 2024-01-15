# asterisk-prometheus-exporter Changelog
## v1.1.0 - 2024-01-15
### Added
- Add metric `version_info` showing the version of the exporter [#12](https://github.com/gonicus/asterisk-prometheus-exporter/pull/12)
- Add the `fully_booted_validation_timeout` configuration value to specify how long to wait for the `FullyBooted` event at startup [#13](https://github.com/gonicus/asterisk-prometheus-exporter/pull/13)

### Changed
- The exporter now waits for the `FullyBooted` event sent by Asterisk. Used to prevent sending actions to early [#13](https://github.com/gonicus/asterisk-prometheus-exporter/pull/13)
- Improve logging [#14](https://github.com/gonicus/asterisk-prometheus-exporter/pull/14)
- Improve docker instructions in `README.md` [#10](https://github.com/gonicus/asterisk-prometheus-exporter/pull/10)
- Update lint and test workflows to only run on the `pull_request` trigger  [#15](https://github.com/gonicus/asterisk-prometheus-exporter/pull/15)

### Fixed
- Fix scrape example in `README.md` [#11](https://github.com/gonicus/asterisk-prometheus-exporter/pull/11)

### Dependencies
Dependencies have been updated with the following pull request: [#4](https://github.com/gonicus/asterisk-prometheus-exporter/pull/4)
- Updated python to `3.12.1`
- Updated prometheus-client to `0.19.0`
- Updated asterisk-ami to `0.1.7`
- Updated jsonschema to `4.20.0`
- Updated Docker image to use `python:3.12.1-alpine`
- Updated Flake8 to run on `ubuntu-22.04`
- Updated Flake8 to use python version `3.12.1`
