# Release Notes

## [0.1.0] - 2024-10-20

Initial version, forked from [ultrafunkamsterdam/nodriver@`1bb6003`](https://github.com/ultrafunkamsterdam/nodriver/commit/1bb6003c7f0db4d3ec05fdf3fc8c8e0804260103) with a variety of improvements.

### Fixed

- `Browser.set_all` cookies function now correctly uses provided cookies @ilkecan
- "successfully removed temp profile" message printed on exit is now only shown only when a profile was actually removed. Message is now logged at debug level instead of printed. @mreiden @stephanlensky
- Fix crash on starting browser in headless mode @ilkecan
- Fix `Browser.close()` method to give the browser instance time to shut down before force killing @slensky
- Many `ruff` lint issues @slensky

### Added

- Support for linting with `ruff` and `mypy`. All `ruff` lints are fixed in the initial release, but many `mypy` issues remain to be fixed at a later date. @slensky
- `py.typed` marker so importing as a library in other packages no longer causes `mypy` errors. @slensky

### Changed

- Project is now built with [`uv`](https://github.com/astral-sh/uv). Automatically install dependencies to a venv with `uv sync`, run commands from the venv with `uv run`, and build the project with `uv build`. See the official [`uv` docs](https://docs.astral.sh/uv/) for more information. @slensky
- Docs migrated from sphinx to [mkdocs-material](https://squidfunk.github.io/mkdocs-material/). @slensky
- `Browser.close()` is now async (so it must be `await`ed) @slensky

### Removed

- Twitter account creation example @slensky