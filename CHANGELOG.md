# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Production-ready rewrite with `yt-dlp` backend.
- Full CLI with `--debug`, `--cookies`, `--output`, `--version`, `--dry-run`, and `--update-ytdlp` flags.
- Video-only download mode (no audio).
- Config file support (`~/.config/mfup/config.toml` and local `mfup.toml`).
- Download resume for interrupted downloads.
- Automatic crash reporting with sensitive-data redaction.
- Cross-platform binary builds via GitHub Releases.
- Comprehensive test suite using `pytest`.
- GitHub Actions CI/CD with smoke tests on built binaries.
- `pyproject.toml` for modern Python packaging.
- MIT license.

### Fixed
- Broken custom scraper rewrite removed; restored `yt-dlp` for reliability.
- Missing `ffmpeg` now produces a clear error message instead of silent failure.
- Import paths standardized for package and PyInstaller compatibility.
- Packaging metadata and README corrected.
- URL validation now rejects non-HTTP(S) schemes.
- Crash reports no longer leak URLs, cookie paths, or output paths.
- `--update-ytdlp` disabled for PyInstaller binaries with clear instructions.
- Retry logic narrowed to network-specific exceptions only.
- Progress hook no longer leaves terminal in a polluted state.
- Windows release smoke test uses correct `.exe` extension.
