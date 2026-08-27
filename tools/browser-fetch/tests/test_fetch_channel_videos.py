import subprocess
import sys


def test_fetch_channel_videos_is_registered():
    """No CLI equivalent of MCP's session.list_tools() exists — the closest
    functional analog is checking `channel` is a real, dispatchable subcommand:
    an unregistered name would make argparse fail with "invalid choice" at the
    top-level command dest instead of reaching this subcommand's own --help.

    Runs the real CLI process directly (not the run_cli fixture) because
    --help writes plain usage text to stdout, not JSON — run_cli's payload
    decoding assumes success (returncode 0) means JSON on stdout, which
    doesn't hold here."""
    proc = subprocess.run(
        [sys.executable, "-m", "browser_fetch.cli", "channel", "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "channel_url" in proc.stdout


def test_fetch_channel_videos_rejects_non_youtube_url(run_cli):
    proc, _ = run_cli("channel", "https://x.com/mattpocockuk")
    assert proc.returncode == 2
    assert "Not a YouTube channel URL" in proc.stderr


def test_fetch_channel_videos_rejects_watch_url(run_cli):
    """A single video URL is not a channel — this skill never ingests one."""
    proc, _ = run_cli("channel", "https://www.youtube.com/watch?v=gaDdrDdczO4")
    assert proc.returncode == 2
    assert "Not a YouTube channel URL" in proc.stderr


def test_fetch_channel_videos_rejects_file_scheme(run_cli):
    proc, _ = run_cli("channel", "file:///etc/passwd")
    assert proc.returncode == 2
    assert "only http/https allowed" in proc.stderr
