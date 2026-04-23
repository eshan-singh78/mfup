"""Tests for mfup CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mfup.cli import (
    _resolve_bool,
    _validate_url,
    build_parser,
    main,
)


class TestValidateUrl:
    def test_valid_youtube_url(self) -> None:
        _validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")  # should not raise

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid URL"):
            _validate_url("not-a-url")

    def test_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid URL"):
            _validate_url("")

    def test_non_http_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="Only http and https"):
            _validate_url("ftp://example.com/video.mp4")

    def test_ftp_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="Only http and https"):
            _validate_url("ftp://example.com/video.mp4")


class TestResolveBool:
    def test_cli_true_overrides_all(self) -> None:
        assert _resolve_bool(False, True, None, False) is True
        assert _resolve_bool(True, True, None, False) is True

    def test_cli_false_overrides_all(self) -> None:
        assert _resolve_bool(True, None, True, False) is False
        assert _resolve_bool(False, None, True, False) is False

    def test_config_used_when_cli_not_set(self) -> None:
        assert _resolve_bool(True, None, None, False) is True
        assert _resolve_bool(False, None, None, True) is False

    def test_default_used_when_nothing_set(self) -> None:
        assert _resolve_bool(None, None, None, True) is True
        assert _resolve_bool(None, None, None, False) is False


class TestBuildParser:
    def test_url_required_without_init_config(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])
        assert args.url is None
        assert args.init_config is False

    def test_parses_url(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
        assert args.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert args.debug is None
        assert args.cookies is None
        assert args.output is None

    def test_parses_debug(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--debug", "https://example.com"])
        assert args.debug is True
        assert args.no_debug is None

    def test_parses_no_debug(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--no-debug", "https://example.com"])
        assert args.no_debug is True
        assert args.debug is None

    def test_parses_cookies(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--cookies", "cookies.txt", "https://example.com"])
        assert args.cookies == "cookies.txt"

    def test_parses_output(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["-o", "downloads", "https://example.com"])
        assert args.output == "downloads"

    def test_parses_resume(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--resume", "https://example.com"])
        assert args.resume is True
        assert args.no_resume is None

    def test_parses_no_resume(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--no-resume", "https://example.com"])
        assert args.no_resume is True
        assert args.resume is None

    def test_parses_config(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--config", "mfup.toml", "https://example.com"])
        assert args.config == "mfup.toml"

    def test_version_flag(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0


class TestInitConfig:
    def test_init_config_writes_file(self, tmp_path: Path) -> None:
        with patch("mfup.cli.write_example_config") as mock_write:
            assert main(["--init-config"]) == 0
            mock_write.assert_called_once()


class TestMain:
    def test_keyboard_interrupt(self) -> None:
        with patch("mfup.cli.prompt_and_download", side_effect=KeyboardInterrupt):
            assert main(["https://example.com"]) == 130

    def test_runtime_error(self) -> None:
        with patch(
            "mfup.cli.prompt_and_download",
            side_effect=RuntimeError("ffmpeg missing"),
        ):
            assert main(["https://example.com"]) == 1

    def test_generic_exception_writes_crash_report(self, tmp_path: Path) -> None:
        with (
            patch(
                "mfup.cli.prompt_and_download",
                side_effect=Exception("boom"),
            ),
            patch("mfup.cli.handle_exception") as mock_handle,
            patch("mfup.cli.print_crash_notice") as mock_notice,
        ):
            mock_handle.return_value = tmp_path / "crash.txt"
            assert main(["https://example.com"]) == 1
            mock_handle.assert_called_once()
            mock_notice.assert_called_once()

    def test_config_not_found(self) -> None:
        with patch(
            "mfup.cli.load_config",
            side_effect=FileNotFoundError("missing.toml"),
        ):
            assert main(["--config", "missing.toml", "https://example.com"]) == 1

    def test_invalid_url(self) -> None:
        assert main(["not-a-url"]) == 1

    def test_main_with_defaults(self) -> None:
        with patch("mfup.cli.prompt_and_download", return_value=0) as mock_download:
            assert main(["https://example.com"]) == 0
            mock_download.assert_called_once()
            _, kwargs = mock_download.call_args
            assert kwargs["debug"] is False
            assert kwargs["resume"] is True

    def test_main_with_config_debug(self) -> None:
        with patch("mfup.cli.prompt_and_download", return_value=0) as mock_download:
            with patch("mfup.cli.load_config", return_value={"debug": True}):
                assert main(["https://example.com"]) == 0
                _, kwargs = mock_download.call_args
                assert kwargs["debug"] is True

    def test_main_with_config_resume_false(self) -> None:
        with patch("mfup.cli.prompt_and_download", return_value=0) as mock_download:
            with patch("mfup.cli.load_config", return_value={"resume": False}):
                assert main(["https://example.com"]) == 0
                _, kwargs = mock_download.call_args
                assert kwargs["resume"] is False

    def test_cli_debug_overrides_config(self) -> None:
        with patch("mfup.cli.prompt_and_download", return_value=0) as mock_download:
            with patch("mfup.cli.load_config", return_value={"debug": False}):
                assert main(["--debug", "https://example.com"]) == 0
                _, kwargs = mock_download.call_args
                assert kwargs["debug"] is True

    def test_cli_no_debug_overrides_config(self) -> None:
        with patch("mfup.cli.prompt_and_download", return_value=0) as mock_download:
            with patch("mfup.cli.load_config", return_value={"debug": True}):
                assert main(["--no-debug", "https://example.com"]) == 0
                _, kwargs = mock_download.call_args
                assert kwargs["debug"] is False

    def test_output_expands_tilde(self) -> None:
        with patch("mfup.cli.prompt_and_download", return_value=0) as mock_download:
            cfg = {"output_dir": "~/Downloads"}
            with patch("mfup.cli.load_config", return_value=cfg):
                assert main(["https://example.com"]) == 0
                _, kwargs = mock_download.call_args
                assert kwargs["output"].startswith("/")
                assert "Downloads" in kwargs["output"]

    def test_update_ytdlp_flag(self) -> None:
        with patch("mfup.cli.update_ytdlp", return_value=0) as mock_update:
            assert main(["--update-ytdlp"]) == 0
            mock_update.assert_called_once()

    def test_video_only_no_audio_choice(self) -> None:
        select_mock = MagicMock()
        select_mock.execute.side_effect = [
            "Video only (no audio)",
            "720",
        ]
        with patch("mfup.cli.inquirer.select", return_value=select_mock):
            with patch("mfup.cli.get_video_formats", return_value=["720", "1080"]):
                with patch("mfup.cli.download_video_only") as mock_download:
                    assert main(["https://example.com"]) == 0
                    mock_download.assert_called_once()
                    _, kwargs = mock_download.call_args
                    assert kwargs["debug"] is False
                    assert kwargs["resume"] is True

    def test_dry_run_flag(self, tmp_path: Path) -> None:
        with patch(
            "mfup.cli.simulate_download",
            return_value={
                "title": "Test Video",
                "duration": 120,
                "uploader": "Tester",
                "formats": [
                    {"vcodec": "h264", "height": 720},
                ],
            },
        ) as mock_sim:
            assert main(["--dry-run", "https://example.com"]) == 0
            mock_sim.assert_called_once()

    def test_invalid_output_dir(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "does_not_exist"
        assert main(["-o", str(bad_dir), "https://example.com"]) == 1

    def test_read_only_output_dir(self, tmp_path: Path) -> None:
        ro_dir = tmp_path / "readonly"
        ro_dir.mkdir()
        with patch("mfup.cli.os.access", return_value=False):
            assert main(["-o", str(ro_dir), "https://example.com"]) == 1

    def test_missing_cookies_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.txt"
        assert main(["--cookies", str(missing), "https://example.com"]) == 1
