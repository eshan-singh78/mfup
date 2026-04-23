"""Tests for mfup crash reporter."""

from pathlib import Path
from unittest.mock import patch

import pytest
from mfup.crash_reporter import (
    _MAX_CRASH_REPORTS,
    _rotate_crash_reports,
    _sanitize_argv,
    handle_exception,
    print_crash_notice,
)


class TestHandleException:
    def test_writes_crash_report(self, tmp_path: Path) -> None:
        with patch("mfup.crash_reporter._crashes_dir", return_value=tmp_path):
            exc = ValueError("something broke")
            report_path = handle_exception(exc)
            assert report_path.exists()
            content = report_path.read_text()
            assert "mfup Crash Report" in content
            assert "something broke" in content
            assert "ValueError" in content

    def test_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "crashes"
        with patch("mfup.crash_reporter._crashes_dir", return_value=nested):
            handle_exception(RuntimeError("boom"))
            assert nested.exists()

    def test_rotation_deletes_oldest(self, tmp_path: Path) -> None:
        crash_dir = tmp_path / "crashes"
        crash_dir.mkdir()
        # Create more than the max allowed reports
        for i in range(_MAX_CRASH_REPORTS + 3):
            report = crash_dir / f"crash_20240101_00000{i}.txt"
            report.write_text(f"report {i}")

        with patch("mfup.crash_reporter._crashes_dir", return_value=crash_dir):
            handle_exception(RuntimeError("new crash"))

        reports = sorted(crash_dir.glob("crash_*.txt"))
        assert len(reports) == _MAX_CRASH_REPORTS


class TestRotateCrashReports:
    def test_deletes_oldest_when_over_limit(self, tmp_path: Path) -> None:
        crash_dir = tmp_path / "crashes"
        crash_dir.mkdir()
        for i in range(5):
            report = crash_dir / f"crash_20240101_00000{i}.txt"
            report.write_text(f"report {i}")
            # Touch files with different mtimes
            import time

            time.sleep(0.01)

        _rotate_crash_reports(crash_dir, max_reports=3)
        reports = sorted(crash_dir.glob("crash_*.txt"))
        assert len(reports) == 3

    def test_does_nothing_when_under_limit(self, tmp_path: Path) -> None:
        crash_dir = tmp_path / "crashes"
        crash_dir.mkdir()
        for i in range(2):
            report = crash_dir / f"crash_20240101_00000{i}.txt"
            report.write_text(f"report {i}")

        _rotate_crash_reports(crash_dir, max_reports=10)
        reports = list(crash_dir.glob("crash_*.txt"))
        assert len(reports) == 2


class TestSanitizeArgv:
    def test_redacts_url(self) -> None:
        argv = ["mfup", "https://example.com/watch?v=secret"]
        assert _sanitize_argv(argv) == ["mfup", "<redacted_url>"]

    def test_redacts_cookies_and_output(self) -> None:
        argv = ["mfup", "--cookies", "/secret/cookies.txt", "-o", "/out", "https://x"]
        result = _sanitize_argv(argv)
        assert result[1] == "--cookies"
        assert result[2] == "<redacted>"
        assert result[3] == "-o"
        assert result[4] == "<redacted>"
        assert result[5] == "<redacted_url>"

    def test_redacts_key_value_equals_syntax(self) -> None:
        argv = ["mfup", "--cookies=/secret/cookies.txt", "--output=/out", "https://x"]
        result = _sanitize_argv(argv)
        assert result[1] == "--cookies=<redacted>"
        assert result[2] == "--output=<redacted>"
        assert result[3] == "<redacted_url>"


class TestPrintCrashNotice:
    def test_prints_path(self, capsys: pytest.CaptureFixture[str]) -> None:
        path = Path("/tmp/crash.txt")
        print_crash_notice(path)
        captured = capsys.readouterr()
        assert "mfup crashed" in captured.err
        assert str(path) in captured.err
