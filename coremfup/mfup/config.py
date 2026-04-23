"""Config file loading for mfup.

Supports ``~/.config/mfup/config.toml`` (platform-specific via
``platformdirs``) and an optional local ``mfup.toml`` in the current
working directory.  CLI arguments override config file values.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, cast

from platformdirs import user_config_dir

logger = logging.getLogger(__name__)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

DEFAULT_CONFIG: dict[str, Any] = {
    "output_dir": None,
    "cookies": None,
    "audio_format": "mp3",
    "debug": False,
    "resume": True,
}


def _config_path(name: str = "config.toml") -> Path:
    """Return the platform-specific user config directory for mfup."""
    return Path(user_config_dir("mfup", "eshan-singh78")) / name


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file, returning an empty dict on failure."""
    try:
        with path.open("rb") as fh:
            return cast(dict[str, Any], tomllib.load(fh))
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as exc:
        logger.warning("Invalid TOML in %s: %s", path, exc)
        return {}


def _expand_paths(cfg: dict[str, Any]) -> dict[str, Any]:
    """Expand ``~`` in path-like config values.

    Args:
        cfg: Raw config dictionary.

    Returns:
        Config dictionary with expanded paths.
    """
    for key in ("output_dir", "cookies"):
        val = cfg.get(key)
        if val is not None:
            cfg[key] = os.path.expanduser(str(val))
    return cfg


def load_config(config_file: str | None = None) -> dict[str, Any]:
    """Load and merge configuration sources.

    Priority (highest first):
        1. Explicit ``config_file`` argument.
        2. Local ``mfup.toml`` in the current working directory.
        3. Platform-specific user config file.

    Args:
        config_file: Optional explicit path to a config file.

    Returns:
        A dictionary of merged configuration values.  Unset keys retain
        ``None`` defaults so the CLI can distinguish "not configured"
        from "explicitly set to default".
    """
    cfg = DEFAULT_CONFIG.copy()

    # Lowest priority: platform-specific user config
    user_cfg = _config_path()
    if user_cfg.exists():
        cfg.update(_load_toml(user_cfg))

    # Middle priority: local mfup.toml
    local_cfg = Path("mfup.toml")
    if local_cfg.exists():
        cfg.update(_load_toml(local_cfg))

    # Highest priority: explicit file
    if config_file:
        explicit = Path(config_file)
        if not explicit.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        cfg.update(_load_toml(explicit))

    return _expand_paths(cfg)


def write_example_config(path: Path | None = None) -> None:
    """Write a commented example config file to disk.

    Args:
        path: Destination path.  Defaults to the platform-specific
            user config file.
    """
    dest = path or _config_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    example = """\
# mfup configuration file
# Place this file at ~/.config/mfup/config.toml (or mfup.toml locally).

# Default output directory for downloads.
# output_dir = "~/Downloads"

# Path to a Netscape-format cookies.txt file.
# cookies = "~/cookies.txt"

# Default audio format for audio-only downloads.
# audio_format = "mp3"

# Enable verbose yt-dlp logs by default.
# debug = false

# Resume incomplete downloads by default.
# resume = true
"""
    dest.write_text(example)
    print(f"Example config written to: {dest}")
