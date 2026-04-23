"""mfup CLI entry point."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from urllib.parse import urlparse

from InquirerPy import inquirer

from mfup import __version__
from mfup.config import load_config, write_example_config
from mfup.crash_reporter import handle_exception, print_crash_notice
from mfup.downloader import (
    download_audio,
    download_video,
    download_video_only,
    get_video_formats,
    simulate_download,
)

logger = logging.getLogger(__name__)


def _setup_logging(debug: bool) -> None:
    """Configure logging level and format."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


_ALLOWED_SCHEMES = {"http", "https"}


def _validate_url(url: str) -> None:
    """Validate that the provided string looks like an HTTP(S) URL.

    Args:
        url: The URL string to validate.

    Raises:
        ValueError: If the URL is missing a scheme, netloc, or uses
            a non-HTTP(S) scheme.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            f"Invalid URL: {url!r}. "
            "Expected a full URL such as https://www.youtube.com/watch?v=..."
        )
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Invalid URL scheme: {parsed.scheme!r}. "
            "Only http and https URLs are supported."
        )


def _resolve_bool(
    cfg_value: bool | None,
    cli_true: bool | None,
    cli_false: bool | None,
    default: bool,
) -> bool:
    """Resolve a boolean value with CLI flags overriding config.

    Priority: explicit CLI flag > config file > default.

    Args:
        cfg_value: Value from config file, or None if unset.
        cli_true: Value from --flag, or None if not passed.
        cli_false: Value from --no-flag, or None if not passed.
        default: Fallback when neither CLI nor config provides a value.

    Returns:
        The resolved boolean.
    """
    if cli_true is True:
        return True
    if cli_false is True:
        return False
    if cfg_value is not None:
        return bool(cfg_value)
    return default


def update_ytdlp() -> int:
    """Update yt-dlp to the latest version via pip.

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    if getattr(sys, "frozen", False):
        print(
            "Auto-update is not available for standalone binaries.\n"
            "Please download the latest release from:\n"
            "  https://github.com/eshan-singh78/mfup/releases",
            file=sys.stderr,
        )
        return 1
    try:
        print("Updating yt-dlp...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("yt-dlp updated successfully.")
            return 0
        print(f"yt-dlp update failed:\n{result.stderr}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"yt-dlp update failed: {exc}", file=sys.stderr)
        return 1


def _ytdlp_version() -> str:
    """Return the installed yt-dlp version string."""
    try:
        import yt_dlp

        return str(yt_dlp.__version__)
    except Exception:
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="mfup",
        description="mfup - Media Fire Up: Download YouTube videos and audio",
    )
    parser.add_argument("url", nargs="?", help="Media URL (YouTube)")
    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help="Show detailed yt-dlp logs",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        default=None,
        help="Disable verbose yt-dlp logs (overrides config)",
    )
    parser.add_argument(
        "--cookies",
        type=str,
        default=None,
        help="Path to cookies.txt file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output directory for downloads",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a custom config file",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Write an example config file and exit",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=None,
        help="Resume incomplete downloads (default)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        default=None,
        help="Do not resume incomplete downloads",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__} (yt-dlp {_ytdlp_version()})",
    )
    parser.add_argument(
        "--update-ytdlp",
        action="store_true",
        help="Update yt-dlp to the latest version and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )
    return parser


def _prompt_quality(
    url: str,
    cookies: str | None,
    debug: bool,
) -> int | str:
    """Fetch available qualities and prompt the user to pick one.

    Returns:
        Selected quality as an integer height or "best".
    """
    formats = get_video_formats(url, debug=debug, cookies=cookies)
    if not formats or formats == ["best"]:
        print("[!] Could not fetch available qualities. Using 'best'.")
        return "best"
    quality_raw = inquirer.select(  # type: ignore[attr-defined]
        message="Choose video quality:",
        choices=formats,
    ).execute()
    return int(quality_raw) if quality_raw.isdigit() else "best"


def _validate_paths(output: str | None, cookies: str | None) -> None:
    """Validate that output directory and cookies file exist and are usable.

    Args:
        output: Optional output directory path.
        cookies: Optional cookies file path.

    Raises:
        ValueError: If a path is invalid or inaccessible.
    """
    if output:
        if not os.path.isdir(output):
            raise ValueError(
                f"Output directory does not exist or is not a directory: {output}"
            )
        if not os.access(output, os.W_OK):
            raise ValueError(f"Output directory is not writable: {output}")
    if cookies and not os.path.isfile(cookies):
        raise ValueError(f"Cookies file not found: {cookies}")


def prompt_and_download(
    url: str,
    output: str | None,
    cookies: str | None,
    debug: bool,
    resume: bool,
    dry_run: bool = False,
) -> int:
    """Prompt user for choices and dispatch download.

    Args:
        url: Target media URL.
        output: Optional output directory.
        cookies: Optional path to cookies file.
        debug: Enable verbose yt-dlp logging.
        resume: Whether to resume partial downloads.
        dry_run: If True, show metadata without downloading.

    Returns:
        Exit code (0 for success).
    """
    _validate_paths(output, cookies)

    if dry_run:
        print("[dry-run] Fetching metadata...")
        info = simulate_download(url, debug=debug, cookies=cookies)
        print(f"Title: {info.get('title', 'unknown')}")
        print(f"Duration: {info.get('duration', 'unknown')} seconds")
        print(f"Uploader: {info.get('uploader', 'unknown')}")
        formats = info.get("formats", [])
        resolutions = sorted(
            {
                f["height"]
                for f in formats
                if f.get("vcodec") != "none" and f.get("height")
            }
        )
        if resolutions:
            res_str = ", ".join(str(r) for r in resolutions)
            print(f"Available video resolutions: {res_str}p")
        else:
            print("No video resolutions found.")
        return 0

    choice = inquirer.select(  # type: ignore[attr-defined]
        message="What do you want to download?",
        choices=["Audio only", "Video (with audio)", "Video only (no audio)"],
    ).execute()

    if choice == "Video (with audio)":
        quality = _prompt_quality(url, cookies=cookies, debug=debug)
        download_video(
            url,
            quality,
            debug=debug,
            cookies=cookies,
            output_folder=output,
            resume=resume,
        )

    elif choice == "Audio only":
        audio_format = inquirer.select(  # type: ignore[attr-defined]
            message="Choose audio format:",
            choices=["mp3", "wav"],
        ).execute()
        download_audio(
            url,
            audio_format,
            debug=debug,
            cookies=cookies,
            output_folder=output,
            resume=resume,
        )

    elif choice == "Video only (no audio)":
        quality = _prompt_quality(url, cookies=cookies, debug=debug)
        download_video_only(
            url,
            quality,
            debug=debug,
            cookies=cookies,
            output_folder=output,
            resume=resume,
        )

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Optional CLI arguments for testing.

    Returns:
        Exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.init_config:
        write_example_config()
        return 0

    if args.update_ytdlp:
        return update_ytdlp()

    if not args.url:
        parser.error("the following arguments are required: url")

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"[mfup error] {exc}", file=sys.stderr)
        return 1

    # Resolve boolean flags with proper None-default handling
    debug = _resolve_bool(cfg.get("debug"), args.debug, args.no_debug, False)
    resume = _resolve_bool(cfg.get("resume"), args.resume, args.no_resume, True)

    # Resolve paths: CLI overrides config; expand ~ for usability
    output = args.output or cfg.get("output_dir")
    if output:
        output = os.path.expanduser(output)

    cookies = args.cookies or cfg.get("cookies")
    if cookies:
        cookies = os.path.expanduser(cookies)

    try:
        _validate_url(args.url)
    except ValueError as exc:
        print(f"[mfup error] {exc}", file=sys.stderr)
        return 1

    _setup_logging(debug)

    try:
        return prompt_and_download(
            args.url,
            output=output,
            cookies=cookies,
            debug=debug,
            resume=resume,
            dry_run=args.dry_run,
        )
    except RuntimeError as exc:
        logger.error("%s", exc)
        print(f"[mfup error] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as exc:
        logger.exception("Unexpected error")
        report_path = handle_exception(exc)
        print_crash_notice(report_path)
        return 1


if __name__ == "__main__":
    sys.exit(main())
