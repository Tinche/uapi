# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [_Calendar Versioning_](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

<!-- changelog follows -->

## [v23.1.0](https://github.com/tinche/uapi/compare/v22.1.0...HEAD) - UNRELEASED

### Changed

- Add the initial header implementation.
- Endpoints can be excluded from OpenAPI generation by passing them to `app.make_openapi_spec(exclude=...)` or `app.serve_openapi(exclude=...)`.

### Fixed

- Stringified annotations for return types are now handled properly.
- Framework-specific request objects are ignored for OpenAPI.
- Fix OpenAPI generation so items produced by the dependency injection system are properly generated.

## [v22.1.0](https://github.com/tinche/uapi/compare/63cd8336f229f3a007f8fce7e9791b22abaf75d9...v22.1.0) - 2022-12-07

### Changed

- Changelog starts.
