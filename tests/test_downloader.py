"""Tests for mfup downloader."""

import shutil
from unittest.mock import MagicMock, patch

import pytest
import yt_dlp
from mfup.downloader import (
    _download_with_retry,
    _ensure_ffmpeg,
    _get_opts,
    download_video_only,
    get_video_formats,
    get_video_resolutions,
    simulate_download,
)


class TestEnsureFfmpeg:
    def test_when_ffmpeg_missing(self) -> None:
        with patch.object(shutil, "which", return_value=None):
            with pytest.raises(RuntimeError, match="ffmpeg is required"):
                _ensure_ffmpeg()

    def test_when_ffmpeg_present(self) -> None:
        with patch.object(shutil, "which", return_value="/usr/bin/ffmpeg"):
            _ensure_ffmpeg()  # should not raise


class TestGetOpts:
    def test_defaults(self) -> None:
        opts = _get_opts()
        assert opts["quiet"] is True
        assert opts["no_warnings"] is True
        assert opts["noplaylist"] is True
        assert opts["outtmpl"] == "%(title)s.%(ext)s"
        assert opts["socket_timeout"] == 60

    def test_debug_mode(self) -> None:
        opts = _get_opts(debug=True)
        assert opts["quiet"] is False
        assert opts["no_warnings"] is False

    def test_extra_opts(self) -> None:
        opts = _get_opts(extra_opts={"format": "best"})
        assert opts["format"] == "best"

    def test_cookies(self) -> None:
        opts = _get_opts(cookies="cookies.txt")
        assert opts["cookiefile"] == "cookies.txt"

    def test_outtmpl(self) -> None:
        opts = _get_opts(outtmpl="custom.%(ext)s")
        assert opts["outtmpl"] == "custom.%(ext)s"

    def test_resume_default(self) -> None:
        opts = _get_opts()
        assert opts["continuedl"] is True

    def test_no_resume(self) -> None:
        opts = _get_opts(resume=False)
        assert opts["continuedl"] is False


class TestGetVideoResolutions:
    def test_empty_on_download_error(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError(
                "network error"
            )
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            assert get_video_resolutions("https://example.com") == []

    def test_extracts_heights(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = {
                "formats": [
                    {"vcodec": "h264", "height": 720},
                    {"vcodec": "none", "height": 720},  # audio, ignored
                    {"vcodec": "h264", "height": 1080},
                    {"vcodec": "h264", "height": 720},  # duplicate
                ]
            }
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            assert get_video_resolutions("https://example.com") == [720, 1080]

    def test_empty_when_extract_info_returns_none(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = None
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            assert get_video_resolutions("https://example.com") == []


class TestGetVideoFormats:
    def test_returns_best_when_no_resolutions(self) -> None:
        with patch("mfup.downloader.get_video_resolutions", return_value=[]):
            assert get_video_formats("https://example.com") == ["best"]

    def test_returns_strings(self) -> None:
        with patch(
            "mfup.downloader.get_video_resolutions", return_value=[360, 720, 1080]
        ):
            assert get_video_formats("https://example.com") == [
                "360",
                "720",
                "1080",
            ]


class TestDownloadWithRetry:
    def test_success_on_first_attempt(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            _download_with_retry("https://example.com", {})
            mock_ydl.download.assert_called_once_with(["https://example.com"])

    def test_retries_then_succeeds(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.download.side_effect = [
                yt_dlp.utils.DownloadError("transient"),
                None,
            ]
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            with patch("mfup.downloader.time.sleep"):
                _download_with_retry("https://example.com", {}, max_retries=2)
            assert mock_ydl.download.call_count == 2

    def test_raises_after_all_retries_fail(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.download.side_effect = yt_dlp.utils.DownloadError("fatal")
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            with patch("mfup.downloader.time.sleep"):
                with pytest.raises(RuntimeError, match="Download failed after"):
                    _download_with_retry(
                        "https://example.com", {}, max_retries=2, backoff=0.1
                    )
            assert mock_ydl.download.call_count == 2

    def test_retries_on_connection_error(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.download.side_effect = [
                ConnectionError("reset"),
                None,
            ]
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            with patch("mfup.downloader.time.sleep"):
                _download_with_retry("https://example.com", {}, max_retries=2)
            assert mock_ydl.download.call_count == 2


class TestDownloadVideoOnly:
    def test_calls_bestvideo_format(self) -> None:
        with patch("mfup.downloader._download_with_retry") as mock_dl:
            download_video_only("https://example.com", resolution="best")
            opts = mock_dl.call_args[0][1]
            assert opts["format"] == "bestvideo/best"

    def test_calls_specific_resolution(self) -> None:
        with patch("mfup.downloader._download_with_retry") as mock_dl:
            download_video_only("https://example.com", resolution=720)
            opts = mock_dl.call_args[0][1]
            assert opts["format"] == "bestvideo[height<=720]/best"


class TestSimulateDownload:
    def test_returns_metadata(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = {
                "title": "Test",
                "duration": 60,
            }
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            result = simulate_download("https://example.com")
            assert result["title"] == "Test"
            assert result["duration"] == 60

    def test_raises_runtime_error_on_failure(self) -> None:
        with patch("mfup.downloader.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("blocked")
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
            with pytest.raises(RuntimeError, match="Could not fetch video information"):
                simulate_download("https://example.com")
