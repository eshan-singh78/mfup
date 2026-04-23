# mfup

A simple cross-platform CLI tool to download YouTube videos and audio from your terminal.

> **Note:** Currently supports YouTube only.

## Features

- Download audio only (MP3, WAV)
- Download video with audio in available qualities
- Interactive quality and format selection
- Config file support (`~/.config/mfup/config.toml`)
- Download resume for interrupted downloads
- Automatic crash reporting
- Cross-platform binary builds (macOS, Linux, Windows) via GitHub Releases

## Requirements

- **Python 3.9+** (for source/pip install)
- **ffmpeg** must be installed and available on your system PATH. The tool uses ffmpeg for audio extraction and video/audio merging.

## Installation

### From PyPI (when published)

```bash
pip install mfup
```

### From source

```bash
git clone https://github.com/eshan-singh78/mfup.git
cd mfup
pip install -e .
mfup --help
```

### Prebuilt binaries

Download the latest binary for your platform from the [GitHub Releases](https://github.com/eshan-singh78/mfup/releases) page.

## Usage

```bash
mfup <url>
```

Example:

```bash
mfup "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Then choose:

- **Audio only** → MP3 or WAV
- **Video (with audio)** → available qualities fetched from the video
- **Video only (no audio)** → video stream without audio merge

### Options

| Flag | Description |
|------|-------------|
| `--debug` | Show detailed yt-dlp logs |
| `--no-debug` | Disable verbose yt-dlp logs (overrides config) |
| `--cookies FILE` | Path to a Netscape-format cookies.txt file |
| `-o, --output DIR` | Output directory for downloads |
| `--config FILE` | Path to a custom config file |
| `--init-config` | Write an example config file and exit |
| `--resume` | Resume incomplete downloads (default) |
| `--no-resume` | Do not resume incomplete downloads |
| `--update-ytdlp` | Update yt-dlp to the latest version |
| `--dry-run` | Show metadata without downloading |
| `--version` | Show version and exit |

### Config file

Run `mfup --init-config` to create an example config file at `~/.config/mfup/config.toml`.

You can also create a local `mfup.toml` in your working directory for per-project settings.

Supported config keys:

| Key | Description |
|-----|-------------|
| `output_dir` | Default output directory |
| `cookies` | Path to cookies.txt file |
| `audio_format` | Default audio format (`mp3` or `wav`) |
| `debug` | Enable verbose logs by default |
| `resume` | Resume downloads by default |

## Development

Run in development mode:

```bash
cd coremfup
python -m mfup.cli <url>
```

Run tests:

```bash
pytest -v
```

Build a standalone binary locally:

```bash
pyinstaller --onefile --clean --noconfirm --name mfup mfup.spec
```

## License

MIT
