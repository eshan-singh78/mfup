"""Tests for mfup config module."""

from pathlib import Path
from unittest.mock import patch

import pytest
from mfup.config import _expand_paths, _load_toml, load_config


class TestExpandPaths:
    def test_expands_tilde_in_output_dir(self) -> None:
        cfg = {"output_dir": "~/Downloads", "cookies": "~/cookies.txt"}
        expanded = _expand_paths(cfg)
        assert expanded["output_dir"].startswith("/")
        assert expanded["cookies"].startswith("/")
        assert "Downloads" in expanded["output_dir"]

    def test_leaves_none_unchanged(self) -> None:
        cfg = {"output_dir": None, "cookies": None}
        expanded = _expand_paths(cfg)
        assert expanded["output_dir"] is None
        assert expanded["cookies"] is None


class TestLoadToml:
    def test_returns_empty_on_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.toml"
        assert _load_toml(missing) == {}

    def test_loads_valid_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.write_text('output_dir = "/downloads"\ndebug = true\n')
        assert _load_toml(path) == {"output_dir": "/downloads", "debug": True}

    def test_returns_empty_on_invalid(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.toml"
        path.write_text("not valid toml [[[")
        assert _load_toml(path) == {}


class TestLoadConfig:
    def test_returns_defaults_when_no_files(self) -> None:
        with patch.object(Path, "exists", return_value=False):
            cfg = load_config()
            assert cfg["output_dir"] is None
            assert cfg["debug"] is False
            assert cfg["resume"] is True

    def test_explicit_file_overrides(self, tmp_path: Path) -> None:
        path = tmp_path / "custom.toml"
        path.write_text('output_dir = "/tmp"\nresume = false\n')
        cfg = load_config(str(path))
        assert cfg["output_dir"] == "/tmp"
        assert cfg["resume"] is False

    def test_missing_explicit_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.toml")

    def test_expands_tilde_from_config(self, tmp_path: Path) -> None:
        path = tmp_path / "home.toml"
        path.write_text('output_dir = "~/Downloads"\ncookies = "~/cookies.txt"\n')
        cfg = load_config(str(path))
        assert cfg["output_dir"].startswith("/")
        assert cfg["cookies"].startswith("/")
