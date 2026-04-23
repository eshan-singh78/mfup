"""Download backend powered by yt-dlp."""

from __future__ import annotations

import logging
import shutil
import sys
import time
from typing import Any, cast

import yt_dlp

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60  # seconds for yt-dlp network operations


def _ensure_ffmpeg() -> None:
    """Raise RuntimeError if ffmpeg is not found on PATH."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg is required but was not found on your system. "
            "Please install ffmpeg and ensure it is available on your PATH. "
            "See https://ffmpeg.org/download.html for installation instructions."
        )


def _progress_hook(d: dict[str, Any]) -> None:
    """Display download progress to stdout."""
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("_eta_str", "").strip()
        line = f"\rDownloading: {percent} | {speed} | ETA {eta}"
        # Pad with spaces to clear any trailing characters from previous lines
        sys.stdout.write(line.ljust(80) + "\r")
        sys.stdout.flush()
    elif d["status"] == "finished":
        sys.stdout.write("\nDownload complete, finalizing...\n")
        sys.stdout.flush()


def _get_opts(
    debug: bool = False,
    extra_opts: dict[str, Any] | None = None,
    cookies: str | None = None,
    outtmpl: str | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    """Build yt-dlp options dict.

    Args:
        debug: Enable verbose output.
        extra_opts: Additional options merged on top.
        cookies: Path to Netscape cookies file.
        outtmpl: Output filename template.
        resume: Allow yt-dlp to resume partial downloads.

    Returns:
        yt-dlp compatible options dictionary.
    """
    opts: dict[str, Any] = {
        "quiet": not debug,
        "no_warnings": not debug,
        "progress_hooks": [_progress_hook],
        "outtmpl": outtmpl or "%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "geo_bypass": True,
        "continuedl": resume,
        "socket_timeout": DEFAULT_TIMEOUT,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.youtube.com/",
        },
    }
    if cookies:
        opts["cookiefile"] = cookies
    if extra_opts:
        opts.update(extra_opts)
    return opts


def simulate_download(
    url: str,
    debug: bool = False,
    cookies: str | None = None,
) -> dict[str, Any]:
    """Return video metadata without downloading.

    Args:
        url: Target media URL.
        debug: Enable verbose yt-dlp logging.
        cookies: Optional path to cookies file.

    Returns:
        Metadata dictionary extracted by yt-dlp.

    Raises:
        RuntimeError: If the metadata cannot be fetched.
    """
    try:
        with yt_dlp.YoutubeDL(_get_opts(debug, cookies=cookies)) as ydl:
            return cast(dict[str, Any], ydl.extract_info(url, download=False))
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(f"Could not fetch video information: {exc}") from exc


def get_video_resolutions(
    url: str, debug: bool = False, cookies: str | None = None
) -> list[int]:
    """Return sorted list of available video heights.

    Args:
        url: Target media URL.
        debug: Enable verbose yt-dlp logging.
        cookies: Optional path to cookies file.

    Returns:
        Sorted list of resolution heights, or empty list on failure.
    """
    try:
        with yt_dlp.YoutubeDL(_get_opts(debug, cookies=cookies)) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                return []
            resolutions: set[int] = set()
            for fmt in info.get("formats", []):
                if fmt.get("vcodec") != "none" and fmt.get("height"):
                    resolutions.add(fmt["height"])
            return sorted(resolutions)
    except yt_dlp.utils.DownloadError as exc:
        logger.error("Failed to fetch video formats: %s", exc)
        return []


def get_video_formats(
    url: str, debug: bool = False, cookies: str | None = None
) -> list[str]:
    """Return resolution strings for InquirerPy choices.

    Args:
        url: Target media URL.
        debug: Enable verbose yt-dlp logging.
        cookies: Optional path to cookies file.

    Returns:
        List of resolution strings, or ["best"] on failure.
    """
    resolutions = get_video_resolutions(url, debug, cookies)
    if not resolutions:
        return ["best"]
    return [str(r) for r in resolutions]


def _download_with_retry(
    url: str,
    opts: dict[str, Any],
    max_retries: int = 3,
    backoff: float = 2.0,
) -> None:
    """Download with simple exponential backoff retry.

    Retries on yt-dlp ``DownloadError`` as well as network-level
    exceptions such as ``ConnectionError`` and ``TimeoutError``.

    Args:
        url: Target media URL.
        opts: yt-dlp options dictionary.
        max_retries: Maximum number of retries on transient failures.
        backoff: Base backoff multiplier in seconds.
    """
    last_error: Exception | None = None
    retry_exceptions = (
        yt_dlp.utils.DownloadError,
        ConnectionError,
        TimeoutError,
    )
    for attempt in range(1, max_retries + 1):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return
        except retry_exceptions as exc:
            last_error = exc
            logger.warning(
                "Download attempt %d/%d failed: %s", attempt, max_retries, exc
            )
            if attempt < max_retries:
                sleep_time = backoff * (attempt)
                logger.info("Retrying in %.1f seconds...", sleep_time)
                time.sleep(sleep_time)
    raise RuntimeError(
        f"Download failed after {max_retries} attempts. Last error: {last_error}"
    )


def download_video(
    url: str,
    resolution: str | int = "best",
    debug: bool = False,
    cookies: str | None = None,
    output_folder: str | None = None,
    resume: bool = True,
) -> None:
    """Download video with audio.

    Args:
        url: Target media URL.
        resolution: Target height (e.g., "720") or "best".
        debug: Enable verbose yt-dlp logging.
        cookies: Optional path to cookies file.
        output_folder: Optional output directory.
        resume: Allow resuming partial downloads.

    Raises:
        RuntimeError: If ffmpeg is missing or all retries fail.
    """
    _ensure_ffmpeg()
    fmt = (
        f"bestvideo[height<={resolution}]+bestaudio/best"
        if resolution != "best"
        else "bestvideo+bestaudio/best"
    )
    extra: dict[str, Any] = {"format": fmt}
    if output_folder:
        extra["paths"] = {"home": output_folder}
    opts = _get_opts(debug, extra, cookies=cookies, resume=resume)
    _download_with_retry(url, opts)


def download_video_only(
    url: str,
    resolution: str | int = "best",
    debug: bool = False,
    cookies: str | None = None,
    output_folder: str | None = None,
    resume: bool = True,
) -> None:
    """Download video without audio.

    Args:
        url: Target media URL.
        resolution: Target height (e.g., "720") or "best".
        debug: Enable verbose yt-dlp logging.
        cookies: Optional path to cookies file.
        output_folder: Optional output directory.
        resume: Allow resuming partial downloads.

    Raises:
        RuntimeError: If ffmpeg is missing or all retries fail.
    """
    fmt = (
        f"bestvideo[height<={resolution}]/best"
        if resolution != "best"
        else "bestvideo/best"
    )
    extra: dict[str, Any] = {
        "format": fmt,
        "postprocessors": [],
    }
    if output_folder:
        extra["paths"] = {"home": output_folder}
    opts = _get_opts(debug, extra, cookies=cookies, resume=resume)
    _download_with_retry(url, opts)


def download_audio(
    url: str,
    audio_format: str = "mp3",
    debug: bool = False,
    cookies: str | None = None,
    output_folder: str | None = None,
    resume: bool = True,
) -> None:
    """Download and extract audio.

    Args:
        url: Target media URL.
        audio_format: Preferred audio codec (e.g., "mp3" or "wav").
        debug: Enable verbose yt-dlp logging.
        cookies: Optional path to cookies file.
        output_folder: Optional output directory.
        resume: Allow resuming partial downloads.

    Raises:
        RuntimeError: If ffmpeg is missing or all retries fail.
    """
    _ensure_ffmpeg()
    extra: dict[str, Any] = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        ],
    }
    if output_folder:
        extra["paths"] = {"home": output_folder}
    opts = _get_opts(debug, extra, cookies=cookies, resume=resume)
    _download_with_retry(url, opts)
