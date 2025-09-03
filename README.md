# mfup – Media Fire Up  🔥

`mfup` is a simple cross-platform CLI tool to download YouTube videos or audio directly from your terminal.  
For now, it supports YouTube only – more sites coming soon.  

---

## Features
- Download audio only (MP3, WAV)  
- Download video with audio in multiple qualities  
- Interactive prompts in the terminal  
- Cross-platform (binary builds for macOS, Linux, Windows)  
- Single binary – no Python required  

---

## Installation

### macOS / Linux (Homebrew)  
```bash
brew install mfup
````

> Currently available only via Homebrew.
> Scoop (Windows) and APT (Linux) coming soon.

---

## Usage

```bash
mfup <url>
```

Example:

```bash
mfup "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Then choose:

* Audio only → MP3 or WAV
* Video (with audio) → available qualities (360p, 720p, 1080p, etc.)

---

## Development

```bash
git clone https://github.com/eshan-singh78/mfup.git
cd mfup/coremfup
pip install -r requirements.txt
python -m mfup.cli <url>
```

Build a standalone binary:

```bash
pyinstaller --onefile --clean --noconfirm --name mfup mfup/cli.py
```

---

