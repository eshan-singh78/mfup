"""Lightweight crash reporter for mfup.

When an unexpected exception occurs, a detailed crash report is written
to the platform-specific state directory (e.g.
``~/.local/share/mfup/crashes/``).  Users are shown the path so they
can attach it when opening an issue.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from platformdirs import user_state_dir

_MAX_CRASH_REPORTS = 10


def _crashes_dir() -> Path:
    """Return the directory where crash reports are stored."""
    return Path(user_state_dir("mfup", "eshan-singh78")) / "crashes"


def _rotate_crash_reports(
    crash_dir: Path,
    max_reports: int = _MAX_CRASH_REPORTS,
) -> None:
    """Delete oldest crash reports if the count exceeds *max_reports*.

    Args:
        crash_dir: Directory containing crash report files.
        max_reports: Maximum number of reports to retain.
    """
    reports = sorted(crash_dir.glob("crash_*.txt"), key=lambda p: p.stat().st_mtime)
    while len(reports) > max_reports:
        oldest = reports.pop(0)
        oldest.unlink(missing_ok=True)


def _sanitize_argv(argv: list[str]) -> list[str]:
    """Redact sensitive values from the argument list.

    Replaces URL arguments and paths passed to --cookies, --output,
    and --config with placeholders so that crash reports do not
    leak private data. Handles both ``--key value`` and
    ``--key=value`` syntaxes.
    """
    sensitive_keys = {"--cookies", "-o", "--output", "--config"}
    sanitized: list[str] = []
    skip_next = False
    for i, arg in enumerate(argv):
        if skip_next:
            skip_next = False
            continue

        # Handle --key=value syntax (e.g. --cookies=/secret/path)
        if "=" in arg:
            key, _ = arg.split("=", 1)
            if key in sensitive_keys:
                sanitized.append(f"{key}=<redacted>")
                continue

        if arg in sensitive_keys:
            sanitized.append(arg)
            if i + 1 < len(argv):
                sanitized.append("<redacted>")
                skip_next = True
        elif arg.startswith(("http://", "https://")):
            sanitized.append("<redacted_url>")
        else:
            sanitized.append(arg)
    return sanitized


def handle_exception(exc: BaseException) -> Path:
    """Write a crash report and return its path.

    Args:
        exc: The exception that caused the crash.

    Returns:
        Path to the written crash report file.
    """
    crash_dir = _crashes_dir()
    crash_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = crash_dir / f"crash_{timestamp}.txt"

    lines = [
        "mfup Crash Report",
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
        f"Python: {sys.version}",
        f"Platform: {sys.platform}",
        f"Command: {' '.join(_sanitize_argv(sys.argv))}",
        "",
        "Traceback:",
    ]
    lines.extend(traceback.format_exception(type(exc), exc, exc.__traceback__))

    report_path.write_text("\n".join(lines), encoding="utf-8")
    _rotate_crash_reports(crash_dir)
    return report_path


def print_crash_notice(report_path: Path) -> None:
    """Print a user-friendly notice with the crash report location."""
    print(
        f"\n[ mfup crashed ]\n"
        f"A detailed crash report has been saved to:\n"
        f"  {report_path}\n"
        f"Please include this file when reporting the issue.\n",
        file=sys.stderr,
    )
