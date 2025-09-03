# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [_Calendar Versioning_](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

<!-- changelog follows -->

## [v24.1.0](https://github.com/tinche/uapi/compare/v23.3.0...HEAD) - UNRELEASED

### Added

- `typing.Any` is now supported in the OpenAPI schema, rendering to an empty schema.
  ([#58](https://github.com/Tinche/uapi/pull/58))
- Dictionaries are now supported in the OpenAPI schema, rendering to object schemas with `additionalProperties`.
  ([#58](https://github.com/Tinche/uapi/pull/58))
- {meth}`uapi.flask.FlaskApp.run`, {meth}`uapi.quart.QuartApp.run` and {meth}`uapi.starlette.StarletteApp.run` now expose `host` parameters.
  ([#59](https://github.com/Tinche/uapi/pull/59))
- _uapi_ is now tested against Python 3.13 and 3.14.
  ([#60](https://github.com/Tinche/uapi/pull/60) [#65](https://github.com/Tinche/uapi/pull/65))
- Python 3.10 is no longer supported.
  ([#65](https://github.com/Tinche/uapi/pull/65)

## [v23.3.0](https://github.com/tinche/uapi/compare/v23.2.0...v23.3.0) - 2023-12-20

### Changed

- Return types of handlers are now type-checked.
  ([#57](https://github.com/Tinche/uapi/pull/57))
- Introduce [Response Shorthands](https://uapi.threeofwands.com/en/latest/response_shorthands.html), port the `str`, `bytes`, `None` and _attrs_ response types to them.
  ([#57](https://github.com/Tinche/uapi/pull/57))
- Unions containing shorthands and _uapi_ response classes (and any combination of these) are now better supported.
  ([#57](https://github.com/Tinche/uapi/pull/57))
- _uapi_ is now tested against Mypy.
  ([#57](https://github.com/Tinche/uapi/pull/57))

## [v23.2.0](https://github.com/tinche/uapi/compare/v23.1.0...v23.2.0) - 2023-12-10

### Changed

- [`datetime.datetime`](https://docs.python.org/3/library/datetime.html#datetime-objects) and [`datetime.date`](https://docs.python.org/3/library/datetime.html#date-objects) are now supported in the OpenAPI schema, both in models and handler parameters.
  ([#53](https://github.com/Tinche/uapi/pull/53))
- Simple forms are now supported using `uapi.ReqForm[T]`. [Learn more](handlers.md#forms).
  ([#54](https://github.com/Tinche/uapi/pull/54))
- _uapi_ now sorts imports using Ruff.

## [v23.1.0](https://github.com/tinche/uapi/compare/v22.1.0...v23.1.0) - 2023-11-12

### Changed

- Add the initial header implementation.
- Function composition (dependency injection) is now documented.
- Endpoints can be excluded from OpenAPI generation by passing them to `App.make_openapi_spec(exclude=...)` or `App.serve_openapi(exclude=...)`.
- Initial implementation of OpenAPI security schemas, supporting the `apikey` type in Redis session backend.
- Update the Elements OpenAPI UI to better handle cookies.
- Flesh out the documentation for response types.
- Add OpenAPI support for string literal fields.
- Add OpenAPI support for generic _attrs_ classes.
- Add OpenAPI support for unions of a single _attrs_ class and `None` (optionals).
- Properly set the OpenAPI `required` attribute for _attrs_ fields without defaults.
- Add OpenAPI support for primitive types in unions.
- _uapi_ now uses [PDM](https://pdm.fming.dev/latest/).
- Dictionary request bodies and _attrs_ classes with dictionary fields are now supported.
- OpenAPI `operationId` properties for operations are now generated from handler names.
- OpenAPI summaries and descriptions are now supported, and can be overridden.
- `aiohttp.web.StreamResponse` is now handled as the root class of aiohttp responses.
- {meth}`uapi.aiohttp.AiohttpApp.run` now uses the [aiohttp App runners](https://docs.aiohttp.org/en/stable/web_advanced.html#application-runners) internally.
- _uapi_ is now tested against Flask 3.
- _uapi_ is now tested against Python 3.12.

### Fixed

- Stringified annotations for return types are now handled properly.
- Framework-specific request objects are ignored for OpenAPI.
- Fix OpenAPI generation so items produced by the dependency injection system are properly generated.
- Fix OpenAPI generation for models with identical names.
- Fix OpenAPI generation for response models with lists of attrs classes.

## [v22.1.0](https://github.com/tinche/uapi/compare/63cd8336f229f3a007f8fce7e9791b22abaf75d9...v22.1.0) - 2022-12-07

### Changed

- Changelog starts.
